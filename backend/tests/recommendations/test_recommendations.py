import uuid

import pytest

from app.recommendations.application.dto.recommendation_dto import StartSessionDTO
from app.recommendations.application.use_cases.deck_use_cases import (
    GetRecommendationDeckUseCase,
    SwipeRecipeUseCase,
)
from app.recommendations.application.use_cases.session_use_cases import (
    GetDiscoverySessionUseCase,
    ListSwipesUseCase,
    StartDiscoverySessionUseCase,
)
from app.recommendations.domain.entities.discovery_session import (
    DiscoverySession,
    IngredientSource,
    SwipeAction,
)
from app.recommendations.domain.exceptions import (
    DiscoverySessionNotFoundError,
    NoIngredientsAvailableError,
    RecipeAlreadySwipedError,
    RecommendedRecipeNotFoundError,
    SelectedCategoryNotFoundError,
    SelectedIngredientNotFoundError,
    SelectedTagNotFoundError,
)
from app.recommendations.domain.repositories.discovery_session_repository import DiscoverySessionRepository
from app.recommendations.domain.services.compatibility_scorer import CompatibilityScorer
from app.recommendations.domain.services.ports import (
    CandidateRankingPage,
    CandidateRecipe,
    FavoritesGateway,
    KitchenCatalog,
    RecipeCandidateSource,
)
from app.shared.exceptions.domain_exceptions import ValidationError
from app.shared.domain.value_objects.localized_text import LocalizedText

ME = "me"


def new_id() -> str:
    return str(uuid.uuid4())


FLOUR, EGG, SUGAR, COCOA = (new_id() for _ in range(4))
MOLD, MIXER = new_id(), new_id()
CATEGORY, TAG_VEGAN = new_id(), new_id()


def candidate(title, ingredients, equipment=frozenset(), owner="author") -> CandidateRecipe:
    return CandidateRecipe(
        id=new_id(),
        title=title,
        description=None,
        cover_photo_url=None,
        category_name=None,
        difficulty_name=None,
        prep_time_minutes=None,
        servings=None,
        created_by_user_id=owner,
        is_personalization=False,
        source_recipe_title=None,
        tag_names=(),
        ingredient_ids=frozenset(ingredients),
        equipment_ids=frozenset(equipment),
    )


class InMemorySessionRepository(DiscoverySessionRepository):

    def __init__(self) -> None:
        self.items: dict = {}

    async def add(self, session):
        self.items[session.id] = session

    async def update(self, session):
        pass

    async def get_by_id(self, session_id):
        return self.items.get(session_id)


class FakeKitchen(KitchenCatalog):

    def __init__(self, pantry=(), equipment=()) -> None:
        self.pantry = list(pantry)
        self.equipment = list(equipment)
        self.names = {FLOUR: "Harina", EGG: "Huevo", SUGAR: "Azúcar", COCOA: "Cacao", MOLD: "Molde", MIXER: "Batidora"}

    async def pantry_ingredient_ids(self, user_id):
        return self.pantry

    async def user_equipment_ids(self, user_id):
        return self.equipment

    async def ingredient_names(self, ids):
        # Localized, like the real ingredients context.
        return {i: LocalizedText({"es": self.names[i], "en": f"{self.names[i]} (en)"}, original="es") for i in ids if i in self.names}

    async def equipment_names(self, ids):
        return {i: LocalizedText.of(self.names[i], "es") for i in ids if i in self.names}


class FakeRecipeSource(RecipeCandidateSource):
    """Ranks in memory with the weights it is given, like the real SQL ranking does."""

    def __init__(self, *recipes: CandidateRecipe, private: tuple[CandidateRecipe, ...] = ()) -> None:
        self.recipes = {r.id: r for r in (*recipes, *private)}
        self.private_ids = {r.id for r in private}
        self.last_request = None

    def _visible(self, recipe, viewer):
        return recipe is not None and (recipe.id not in self.private_ids or recipe.created_by_user_id == viewer)

    async def rank(self, request):
        self.last_request = request
        scorer = CompatibilityScorer(request.ingredient_weight, request.equipment_weight)
        scored = []
        for recipe in self.recipes.values():
            if not self._visible(recipe, request.viewer_user_id) or recipe.id in request.excluded_recipe_ids:
                continue
            c = scorer.score(recipe.ingredient_ids, recipe.equipment_ids, set(request.ingredient_ids), set(request.equipment_ids))
            if c.matched_ingredient_ids and c.ingredient_score >= request.min_ingredient_score:
                scored.append((c.rank_score, recipe.title, recipe.id))
        scored.sort(key=lambda item: (-item[0], item[1]))
        ids = [rid for _, _, rid in scored]
        return CandidateRankingPage(recipe_ids=ids[request.offset : request.offset + request.limit], total=len(ids))

    async def get_many_visible(self, recipe_ids, viewer_user_id):
        return [self.recipes[r] for r in recipe_ids if self._visible(self.recipes.get(r), viewer_user_id)]

    async def get_visible(self, recipe_id, viewer_user_id):
        recipe = self.recipes.get(recipe_id)
        return recipe if self._visible(recipe, viewer_user_id) else None

    async def category_names(self):
        return {CATEGORY: LocalizedText({"es": "Tortas", "en": "Cakes"}, original="es")}

    async def tag_names(self):
        return {TAG_VEGAN: LocalizedText({"es": "Vegano", "en": "Vegan"}, original="es")}


class FakeFavorites(FavoritesGateway):

    def __init__(self) -> None:
        self.saved: set[tuple[str, str]] = set()

    async def save(self, user_id, recipe_id):
        self.saved.add((user_id, recipe_id))

    async def saved_among(self, user_id, recipe_ids):
        return {r for r in recipe_ids if (user_id, r) in self.saved}


class TestCompatibilityScorer:

    def test_scores(self):
        c = CompatibilityScorer().score(
            frozenset({FLOUR, EGG, SUGAR, COCOA}), frozenset({MOLD, MIXER}), {FLOUR, EGG, SUGAR}, {MOLD}
        )
        assert (c.ingredient_score, c.equipment_score, c.rank_score) == (0.75, 0.5, 0.7)
        assert c.missing_ingredient_ids == {COCOA}
        assert c.missing_equipment_ids == {MIXER}
        assert not c.has_all_equipment

    def test_recipe_without_equipment_misses_nothing(self):
        c = CompatibilityScorer().score(frozenset({FLOUR}), frozenset(), {FLOUR}, set())
        assert (c.equipment_score, c.rank_score, c.has_all_equipment) == (1.0, 1.0, True)

    def test_recipe_without_ingredients_scores_zero(self):
        assert CompatibilityScorer().score(frozenset(), frozenset(), {FLOUR}, set()).ingredient_score == 0.0

    def test_equipment_prioritizes_but_never_dominates(self):
        scorer = CompatibilityScorer()
        all_ingredients_no_mold = scorer.score(frozenset({FLOUR}), frozenset({MOLD}), {FLOUR}, set())
        half_ingredients_with_mold = scorer.score(frozenset({FLOUR, EGG}), frozenset({MOLD}), {FLOUR}, {MOLD})
        assert all_ingredients_no_mold.rank_score > half_ingredients_with_mold.rank_score


class TestDiscoverySession:

    def test_selection_wins_over_pantry_and_is_deduplicated(self):
        session = DiscoverySession.start(ME, [FLOUR, EGG, FLOUR], [SUGAR])
        assert session.ingredient_source is IngredientSource.SELECTION
        assert session.ingredient_ids == [FLOUR, EGG]

    def test_falls_back_to_pantry(self):
        session = DiscoverySession.start(ME, [], [SUGAR])
        assert (session.ingredient_source, session.ingredient_ids) == (IngredientSource.PANTRY, [SUGAR])

    def test_needs_some_ingredient(self):
        with pytest.raises(NoIngredientsAvailableError):
            DiscoverySession.start(ME, [], [])

    @pytest.mark.parametrize("score", [-0.1, 1.1])
    def test_min_score_range(self, score):
        with pytest.raises(ValidationError):
            DiscoverySession.start(ME, [FLOUR], [], min_score=score)

    def test_swipe_once_per_recipe(self):
        session = DiscoverySession.start(ME, [FLOUR], [])
        session.swipe("r1", SwipeAction.SAVED, 0.5)
        session.swipe("r2", SwipeAction.DISCARDED, 0.1)

        with pytest.raises(RecipeAlreadySwipedError):
            session.swipe("r1", SwipeAction.SELECTED, 0.5)
        assert session.swipe_counts() == {SwipeAction.DISCARDED: 1, SwipeAction.SAVED: 1, SwipeAction.SELECTED: 0}


@pytest.fixture
def sessions():
    return InMemorySessionRepository()


@pytest.fixture
def kitchen():
    return FakeKitchen(pantry=[SUGAR], equipment=[MOLD])


@pytest.fixture
def brownie():
    return candidate("Brownie", {FLOUR, EGG, COCOA}, {MOLD})


@pytest.fixture
def pancake():
    return candidate("Panqueque", {FLOUR, EGG}, {MIXER})


@pytest.fixture
def mine():
    return candidate("Mi galleta", {FLOUR}, owner=ME)


@pytest.fixture
def secret():
    return candidate("Privada ajena", {FLOUR})


@pytest.fixture
def recipes(brownie, pancake, mine, secret):
    return FakeRecipeSource(brownie, pancake, candidate("Sin match", {SUGAR}), private=(mine, secret))


@pytest.fixture
def favorites():
    return FakeFavorites()


@pytest.fixture
def start(sessions, kitchen, recipes):
    return StartDiscoverySessionUseCase(sessions, kitchen, recipes)


@pytest.fixture
def deck(sessions, recipes, kitchen, favorites):
    return GetRecommendationDeckUseCase(sessions, recipes, kitchen, favorites, CompatibilityScorer())


@pytest.fixture
def swipe(sessions, recipes, kitchen, favorites):
    return SwipeRecipeUseCase(sessions, recipes, kitchen, favorites, CompatibilityScorer())


class TestSessionUseCases:

    async def test_start_with_selection_and_filters(self, start):
        result = await start.execute(
            StartSessionDTO(ME, [FLOUR.upper(), EGG], category_id=CATEGORY, tag_ids=[TAG_VEGAN])
        )

        assert result.ingredient_source == "selection"
        assert [str(i.name) for i in result.ingredients] == ["Harina", "Huevo"]
        assert str(result.category.name) == "Tortas"
        assert [str(t.name) for t in result.tags] == ["Vegano"]

    async def test_start_from_pantry(self, start):
        result = await start.execute(StartSessionDTO(ME, []))
        assert result.ingredient_source == "pantry"
        assert [str(i.name) for i in result.ingredients] == ["Azúcar"]

    async def test_empty_pantry_and_no_selection(self, sessions, recipes):
        with pytest.raises(NoIngredientsAvailableError):
            await StartDiscoverySessionUseCase(sessions, FakeKitchen(), recipes).execute(StartSessionDTO(ME, []))

    @pytest.mark.parametrize(
        "dto, error",
        [
            (StartSessionDTO(ME, ["garbage"]), SelectedIngredientNotFoundError),
            (StartSessionDTO(ME, [FLOUR], category_id=new_id()), SelectedCategoryNotFoundError),
            (StartSessionDTO(ME, [FLOUR], tag_ids=[TAG_VEGAN, "garbage"]), SelectedTagNotFoundError),
        ],
    )
    async def test_rejects_unknown_references(self, start, sessions, dto, error):
        with pytest.raises(error):
            await start.execute(dto)
        assert sessions.items == {}

    async def test_session_is_private(self, start, sessions, kitchen, recipes):
        session_id = (await start.execute(StartSessionDTO(ME, [FLOUR]))).id
        use_case = GetDiscoverySessionUseCase(sessions, kitchen, recipes)

        assert (await use_case.execute(ME, session_id)).id == session_id
        for user, sid in [("intruder", session_id), (ME, "garbage"), (ME, new_id())]:
            with pytest.raises(DiscoverySessionNotFoundError):
                await use_case.execute(user, sid)


class TestDeck:

    async def test_ranks_visible_matching_recipes(self, start, deck, brownie, pancake, mine):
        session_id = (await start.execute(StartSessionDTO(ME, [FLOUR, EGG]))).id

        page = await deck.execute(ME, session_id)

        # Panqueque: 1.0 ingredients, missing mixer -> 0.8. Mi galleta: 1.0, no equipment -> 1.0.
        # Brownie: 2/3 ingredients, has mold -> 0.7333. Private recipe of others and "Sin match" excluded.
        assert [card.title for card in page.items] == ["Mi galleta", "Panqueque", "Brownie"]
        assert page.total == 3

    async def test_card_explains_itself(self, start, deck, brownie):
        session_id = (await start.execute(StartSessionDTO(ME, [FLOUR, EGG]))).id

        card = next(c for c in (await deck.execute(ME, session_id)).items if c.title == "Brownie")

        assert card.compatibility_score == 0.6667
        assert [str(i.name) for i in card.matched_ingredients] == ["Harina", "Huevo"]
        assert [str(i.name) for i in card.missing_ingredients] == ["Cacao"]
        assert card.has_all_equipment is True
        assert card.is_own is False

    async def test_own_recipe_is_flagged(self, start, deck):
        session_id = (await start.execute(StartSessionDTO(ME, [FLOUR]))).id
        card = next(c for c in (await deck.execute(ME, session_id)).items if c.title == "Mi galleta")
        assert card.is_own is True

    async def test_min_score_filters(self, start, deck):
        session_id = (await start.execute(StartSessionDTO(ME, [FLOUR, EGG], min_score=0.9))).id
        page = await deck.execute(ME, session_id)
        assert "Brownie" not in [card.title for card in page.items]

    async def test_swiped_recipes_leave_the_deck_and_save_goes_to_favorites(
        self, start, deck, swipe, favorites, sessions, pancake
    ):
        session_id = (await start.execute(StartSessionDTO(ME, [FLOUR, EGG]))).id

        result = await swipe.execute(ME, session_id, pancake.id, "saved")

        assert (result.action, result.compatibility_score) == ("saved", 1.0)
        assert (ME, pancake.id) in favorites.saved
        titles = [card.title for card in (await deck.execute(ME, session_id)).items]
        assert "Panqueque" not in titles

    async def test_discard_does_not_save(self, start, swipe, favorites, pancake):
        session_id = (await start.execute(StartSessionDTO(ME, [FLOUR]))).id
        await swipe.execute(ME, session_id, pancake.id, "discarded")
        assert favorites.saved == set()

    async def test_cannot_swipe_invisible_recipe(self, start, swipe, secret):
        session_id = (await start.execute(StartSessionDTO(ME, [FLOUR]))).id
        with pytest.raises(RecommendedRecipeNotFoundError):
            await swipe.execute(ME, session_id, secret.id, "saved")

    async def test_cannot_swipe_twice(self, start, swipe, pancake):
        session_id = (await start.execute(StartSessionDTO(ME, [FLOUR]))).id
        await swipe.execute(ME, session_id, pancake.id, "discarded")
        with pytest.raises(RecipeAlreadySwipedError):
            await swipe.execute(ME, session_id, pancake.id, "selected")

    async def test_new_session_starts_clean(self, start, deck, swipe, pancake):
        first = (await start.execute(StartSessionDTO(ME, [FLOUR]))).id
        await swipe.execute(ME, first, pancake.id, "discarded")

        second = (await start.execute(StartSessionDTO(ME, [FLOUR]))).id

        assert "Panqueque" in [card.title for card in (await deck.execute(ME, second)).items]

    async def test_list_swipes_filters_by_action(self, start, swipe, sessions, brownie, pancake):
        session_id = (await start.execute(StartSessionDTO(ME, [FLOUR]))).id
        await swipe.execute(ME, session_id, brownie.id, "selected")
        await swipe.execute(ME, session_id, pancake.id, "discarded")

        selected = await ListSwipesUseCase(sessions).execute(ME, session_id, action="selected")
        everything = await ListSwipesUseCase(sessions).execute(ME, session_id)

        assert [s.recipe_id for s in selected.items] == [brownie.id]
        assert everything.total == 2

    async def test_ranking_request_uses_scorer_weights_and_exclusions(self, start, deck, swipe, recipes, pancake):
        session_id = (await start.execute(StartSessionDTO(ME, [FLOUR], category_id=CATEGORY))).id
        await swipe.execute(ME, session_id, pancake.id, "discarded")

        await deck.execute(ME, session_id, limit=5, offset=0)

        request = recipes.last_request
        assert (request.ingredient_weight, request.equipment_weight) == (0.8, 0.2)
        assert request.excluded_recipe_ids == [pancake.id]
        assert request.equipment_ids == [MOLD]
        assert request.category_id == CATEGORY
        assert request.limit == 5
