from dataclasses import replace
from datetime import timedelta

import pytest

from app.portfolio.application.dto.portfolio_dto import GetPortfolioDTO
from app.portfolio.application.public.favorites_service import FavoritesService
from app.portfolio.application.use_cases.favorite_use_cases import (
    GetFavoriteStatusUseCase,
    SaveRecipeUseCase,
    UnsaveRecipeUseCase,
)
from app.portfolio.application.use_cases.get_portfolio_summary_use_case import GetPortfolioSummaryUseCase
from app.portfolio.application.use_cases.get_portfolio_use_case import GetPortfolioUseCase
from app.portfolio.application.use_cases.portfolio_reader import PortfolioReader
from app.portfolio.domain.entities.portfolio_entry import PortfolioItemKind, build_portfolio
from app.portfolio.domain.entities.saved_recipe import SavedRecipe
from app.portfolio.domain.exceptions import CannotSaveOwnRecipeError, PortfolioRecipeNotFoundError
from tests.portfolio.fakes import (
    FakeRecipeCatalog,
    InMemorySavedRecipeRepository,
    make_snapshot,
)

ME = "me"


@pytest.fixture
def catalog():
    return FakeRecipeCatalog()


@pytest.fixture
def saved_repo():
    return InMemorySavedRecipeRepository()


@pytest.fixture
def save(saved_repo, catalog):
    return SaveRecipeUseCase(saved_repo, catalog)


@pytest.fixture
def portfolio(saved_repo, catalog):
    return GetPortfolioUseCase(PortfolioReader(saved_repo, catalog))


class TestRecipeSnapshot:

    def test_personalization_and_ownership(self):
        recipe = make_snapshot(owner=ME, source_recipe_id="src")
        assert recipe.is_personalization
        assert recipe.is_owned_by(ME)
        assert not recipe.is_owned_by("other")

    def test_matches_category_and_all_tags(self):
        recipe = make_snapshot(category_id="cat", tag_ids=frozenset({"a", "b"}))
        assert recipe.matches(None, [])
        assert recipe.matches("cat", ["a"])
        assert recipe.matches("cat", ["a", "b"])
        assert not recipe.matches("other", [])
        assert not recipe.matches(None, ["a", "c"])


class TestSavedRecipe:

    def test_cannot_save_own_recipe(self):
        with pytest.raises(CannotSaveOwnRecipeError):
            SavedRecipe.save(ME, make_snapshot(owner=ME))


class TestBuildPortfolio:

    def test_classifies_and_sorts_newest_first(self):
        original = make_snapshot("Original", owner=ME, created_minutes=1)
        personalized = make_snapshot("Variant", owner=ME, source_recipe_id="x", created_minutes=3)
        favorite = make_snapshot("Fav")
        saved = SavedRecipe.save(ME, favorite)
        saved.saved_at = original.created_at + timedelta(minutes=1)

        entries = build_portfolio(ME, [original, personalized], [saved], {favorite.id: favorite})

        assert [(e.recipe.title, e.kind) for e in entries] == [
            ("Variant", PortfolioItemKind.PERSONALIZED),
            ("Fav", PortfolioItemKind.SAVED),
            ("Original", PortfolioItemKind.ORIGINAL),
        ]

    def test_skips_saved_recipes_no_longer_visible(self):
        gone = make_snapshot("Gone")
        saved = SavedRecipe.save(ME, gone)

        assert build_portfolio(ME, [], [saved], {}) == []


class TestFavorites:

    async def test_save_is_idempotent(self, save, catalog, saved_repo):
        recipe = catalog.add(make_snapshot())

        first = await save.execute(ME, recipe.id)
        second = await save.execute(ME, recipe.id)

        assert len(saved_repo.items) == 1
        assert first.added_at == second.added_at
        assert first.kind == "saved"

    async def test_cannot_save_private_recipe_of_other_user(self, save, catalog):
        recipe = catalog.add(make_snapshot(is_public=False))

        with pytest.raises(PortfolioRecipeNotFoundError):
            await save.execute(ME, recipe.id)

    async def test_cannot_save_unknown_recipe(self, save):
        with pytest.raises(PortfolioRecipeNotFoundError):
            await save.execute(ME, "missing")

    async def test_cannot_save_own_recipe(self, save, catalog):
        recipe = catalog.add(make_snapshot(owner=ME))

        with pytest.raises(CannotSaveOwnRecipeError):
            await save.execute(ME, recipe.id)

    async def test_unsave_is_idempotent(self, save, catalog, saved_repo):
        recipe = catalog.add(make_snapshot())
        await save.execute(ME, recipe.id)

        await UnsaveRecipeUseCase(saved_repo).execute(ME, recipe.id)
        await UnsaveRecipeUseCase(saved_repo).execute(ME, recipe.id)

        assert saved_repo.items == []

    async def test_status_deduplicates_and_keeps_order(self, save, catalog, saved_repo):
        a = catalog.add(make_snapshot("A"))
        b = catalog.add(make_snapshot("B"))
        await save.execute(ME, b.id)

        statuses = await GetFavoriteStatusUseCase(saved_repo).execute(ME, [b.id, a.id, b.id])

        assert [(s.recipe_id, s.is_saved) for s in statuses] == [(b.id, True), (a.id, False)]
        assert statuses[0].saved_at is not None
        assert statuses[1].saved_at is None

    async def test_favorites_service(self, save, catalog, saved_repo):
        a = catalog.add(make_snapshot("A"))
        b = catalog.add(make_snapshot("B"))
        service = FavoritesService(save, saved_repo)

        await service.save(ME, a.id)

        assert await service.saved_among(ME, [a.id, b.id]) == {a.id}


class TestGetPortfolio:

    @pytest.fixture
    async def populated(self, catalog, save):
        catalog.add(make_snapshot("Pan de ajo", owner=ME, category_id="salado", created_minutes=1))
        catalog.add(
            make_snapshot("Brownie vegano", owner=ME, source_recipe_id="src", tag_ids=frozenset({"vegano"}), created_minutes=2)
        )
        fav = catalog.add(make_snapshot("Brownie clásico", tag_ids=frozenset({"chocolate"})))
        catalog.add(make_snapshot("Not mine and not saved"))
        await save.execute(ME, fav.id)

    async def test_lists_everything(self, portfolio, populated):
        page = await portfolio.execute(GetPortfolioDTO(user_id=ME))
        assert page.total == 3
        assert {item.kind for item in page.items} == {"original", "personalized", "saved"}

    @pytest.mark.parametrize(
        "filters, expected",
        [
            ({"kind": "saved"}, ["Brownie clásico"]),
            ({"kind": "original"}, ["Pan de ajo"]),
            ({"query": "  BROWNIE "}, ["Brownie vegano", "Brownie clásico"]),
            ({"category_id": "salado"}, ["Pan de ajo"]),
            ({"tag_ids": ["vegano"]}, ["Brownie vegano"]),
            ({"tag_ids": ["vegano", "chocolate"]}, []),
        ],
    )
    async def test_filters(self, portfolio, populated, filters, expected):
        page = await portfolio.execute(GetPortfolioDTO(user_id=ME, **filters))
        assert sorted(item.title for item in page.items) == sorted(expected)
        assert page.total == len(expected)

    async def test_paginates_after_filtering(self, portfolio, populated):
        page = await portfolio.execute(GetPortfolioDTO(user_id=ME, limit=2, offset=2))
        assert len(page.items) == 1
        assert page.total == 3

    async def test_private_favorite_disappears(self, portfolio, populated, catalog):
        fav = next(r for r in catalog.recipes.values() if r.title == "Brownie clásico")
        catalog.add(replace(fav, is_public=False))  # author made it private

        page = await portfolio.execute(GetPortfolioDTO(user_id=ME, kind="saved"))

        assert page.total == 0

    async def test_summary(self, saved_repo, catalog, populated):
        summary = await GetPortfolioSummaryUseCase(PortfolioReader(saved_repo, catalog)).execute(ME)
        assert (summary.original_count, summary.personalized_count, summary.saved_count, summary.total) == (1, 1, 1, 3)
