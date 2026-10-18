"""Repository-level checks of what only a real Postgres can tell: constraints and SQL edge cases."""
from __future__ import annotations

import uuid
from decimal import Decimal

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.recipes.domain.entities.recipe import IngredientLine, Recipe, StepDraft
from app.recipes.domain.repositories.recipe_repository import IngredientOverlapQuery
from app.recipes.infraestructure.persistence.models.recipe_step_model import RecipeStepModel
from app.recipes.infraestructure.persistence.repositories.sqlalchemy_recipe_repository import (
    SqlAlchemyRecipeRepository,
)

AUTHOR = str(uuid.uuid4())


async def seeded_ids(db_session) -> dict[str, str]:
    rows = await db_session.execute(
        text("SELECT name, id FROM ingredients WHERE name IN ('Harina todo uso (0000)', 'Manteca', 'Huevo, clara')")
    )
    ids = {name: str(row_id) for name, row_id in rows.all()}
    gram = (await db_session.execute(text("SELECT id FROM units WHERE abbreviation = 'g'"))).scalar_one()
    return {"flour": ids["Harina todo uso (0000)"], "butter": ids["Manteca"], "egg_white": ids["Huevo, clara"], "g": str(gram)}


async def store_user(db_session, user_id: str) -> None:
    await db_session.execute(
        text("INSERT INTO users (id, email, hashed_password, full_name) VALUES (:id, :email, 'x', 'Test')"),
        {"id": user_id, "email": f"{user_id}@example.com"},
    )


def recipe(ids, title, ingredients, owner=AUTHOR, **extra) -> Recipe:
    return Recipe.create(
        created_by_user_id=owner,
        title=title,
        is_public=True,
        ingredients=[IngredientLine(ids[name], Decimal("100"), ids["g"]) for name in ingredients],
        steps=[StepDraft("Mezclar"), StepDraft("Hornear")],
        **extra,
    )


class TestConstraints:

    async def test_duplicate_step_numbers_fail_at_commit(self, db_session):
        """Guards the fixture itself: deferred constraints must be checked even though tests roll back."""
        ids = await seeded_ids(db_session)
        await store_user(db_session, AUTHOR)
        stored = recipe(ids, "Dup", ["flour"])
        await SqlAlchemyRecipeRepository(db_session).add(stored)
        duplicate = RecipeStepModel(id=uuid.uuid4(), recipe_id=stored.id.value, step_number=1, instructions="Duplicado")
        db_session.add(duplicate)
        await db_session.flush()  # deferred: no error yet

        with pytest.raises(IntegrityError):
            async with db_session.begin_nested():
                await db_session.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))

        # Still pending: without this cleanup the fixture's own check fails the teardown (as it should).
        await db_session.delete(duplicate)
        await db_session.flush()

    async def test_swapping_step_numbers_is_allowed(self, db_session):
        ids = await seeded_ids(db_session)
        await store_user(db_session, AUTHOR)
        repository = SqlAlchemyRecipeRepository(db_session)
        stored = recipe(ids, "Swap", ["flour"])
        await repository.add(stored)
        first, second = stored.steps

        stored.replace_steps([StepDraft("Hornear", id=second.id), StepDraft("Mezclar", id=first.id)])
        await repository.update(stored)
        await db_session.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))

        reloaded = await repository.get_by_id(stored.id)
        assert [(s.id, s.step_number) for s in reloaded.steps] == [(second.id, 1), (first.id, 2)]


class TestRanking:

    async def test_min_score_and_tie_break(self, db_session):
        ids = await seeded_ids(db_session)
        await store_user(db_session, AUTHOR)
        repository = SqlAlchemyRecipeRepository(db_session)
        both = recipe(ids, "B ambos", ["flour", "butter"])
        both_alpha = recipe(ids, "A ambos", ["flour", "butter"])
        half = recipe(ids, "Mitad", ["flour", "egg_white"])
        for item in (both, both_alpha, half):
            await repository.add(item)

        def query(**extra):
            return IngredientOverlapQuery(
                viewer_user_id=str(uuid.uuid4()),
                ingredient_ids=[ids["flour"], ids["butter"]],
                equipment_ids=[],
                ingredient_weight=0.8,
                equipment_weight=0.2,
                **extra,
            )

        ranked = await repository.rank_by_ingredient_overlap(query())
        assert ranked.recipe_ids == [both_alpha.id, both.id, half.id]  # same score: alphabetical

        strict = await repository.rank_by_ingredient_overlap(query(min_ingredient_score=0.75))
        assert (strict.recipe_ids, strict.total) == ([both_alpha.id, both.id], 2)

        excluded = await repository.rank_by_ingredient_overlap(query(excluded_recipe_ids=[both_alpha.id]))
        assert excluded.recipe_ids == [both.id, half.id]

    async def test_repeated_ingredient_counts_once(self, db_session):
        ids = await seeded_ids(db_session)
        await store_user(db_session, AUTHOR)
        repository = SqlAlchemyRecipeRepository(db_session)
        # Flour twice (e.g. dough + dusting) and butter: 2 distinct ingredients, the user has 1 -> 0.5.
        stored = recipe(ids, "Masa", ["flour", "flour", "butter"])
        await repository.add(stored)

        half = await repository.rank_by_ingredient_overlap(
            IngredientOverlapQuery(str(uuid.uuid4()), [ids["flour"]], [], 1.0, 0.0, min_ingredient_score=0.5)
        )
        more = await repository.rank_by_ingredient_overlap(
            IngredientOverlapQuery(str(uuid.uuid4()), [ids["flour"]], [], 1.0, 0.0, min_ingredient_score=0.51)
        )

        assert (half.recipe_ids, more.recipe_ids) == ([stored.id], [])
