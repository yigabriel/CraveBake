from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from app.preparation.application.mappers.preparation_assembler import PreparationAssembler
from app.preparation.application.use_cases.preparation_use_cases import (
    GetPreparationUseCase,
    ListPreparationsUseCase,
    PreparationProgressUseCases,
    StartPreparationUseCase,
)
from app.preparation.domain.entities.preparation_session import PreparationSession, PreparationStatus
from app.preparation.domain.exceptions import (
    PreparationNotFoundError,
    PreparationNotInProgressError,
    PreparationRecipeNotFoundError,
    PreparationStepNotFoundError,
    StepHasNoTimerError,
)
from app.preparation.domain.repositories.preparation_session_repository import (
    PreparationPage,
    PreparationSessionRepository,
)
from app.preparation.domain.services.ports import (
    IngredientToPrepare,
    QuantityDisplay,
    RecipeSource,
    RecipeToPrepare,
    ShownQuantity,
    StepToPrepare,
)
from app.shared.domain.value_objects.localized_text import LocalizedText

ME = "me"
NOW = datetime(2026, 5, 1, 12, 0, tzinfo=timezone.utc)


def make_recipe(recipe_id: str = "recipe-1", steps: int = 3, timer_on: int | None = 2) -> RecipeToPrepare:
    return RecipeToPrepare(
        id=recipe_id,
        title="Brownies",
        cover_photo_url=None,
        servings=8,
        ingredients=[
            IngredientToPrepare("sugar", LocalizedText({"es": "Azúcar", "en": "Sugar"}), Decimal("1"), "cup-id", "cup", None, position=2),
            IngredientToPrepare("flour", LocalizedText({"es": "Harina", "en": "Flour"}), Decimal("2"), "cup-id", "cup", "tamizada", position=1),
        ],
        # Given out of order on purpose: the session must sort them.
        steps=[
            StepToPrepare(f"s{n}", n, f"Paso {n}", None, 600 if n == timer_on else None, None)
            for n in reversed(range(1, steps + 1))
        ],
    )


class FakeRecipeSource(RecipeSource):

    def __init__(self, *recipes: RecipeToPrepare) -> None:
        self.recipes = {r.id: r for r in recipes}

    async def get_recipe_to_prepare(self, recipe_id, viewer_user_id):
        return self.recipes.get(recipe_id)


class FakeQuantityDisplay(QuantityDisplay):
    """Pretends every quantity converts to grams at 100 g per unit."""

    def __init__(self) -> None:
        self.calls = 0

    async def show_in(self, quantities, unit_system):
        self.calls += 1
        return [ShownQuantity(q.quantity * 100, "g", converted=True) for q in quantities]


class InMemoryPreparationRepository(PreparationSessionRepository):

    def __init__(self) -> None:
        self.items: list[PreparationSession] = []

    async def add(self, session):
        self.items.append(session)

    async def update(self, session):
        pass  # held by reference

    async def get_by_id(self, session_id):
        return next((s for s in self.items if s.id == session_id), None)

    async def find_in_progress(self, user_id, recipe_id):
        return next(
            (s for s in self.items if s.user_id == user_id and s.recipe_id == recipe_id and s.is_in_progress), None
        )

    async def list_by_user(self, user_id, status, recipe_id, limit, offset):
        matches = [
            s
            for s in sorted(self.items, key=lambda s: s.started_at, reverse=True)
            if s.user_id == user_id
            and (status is None or s.status == status)
            and (recipe_id is None or s.recipe_id == recipe_id)
        ]
        return PreparationPage(items=matches[offset : offset + limit], total=len(matches))


class TestPreparationSession:

    def test_start_copies_and_sorts_recipe(self):
        session = PreparationSession.start(ME, make_recipe())

        assert [s.step_number for s in session.steps] == [1, 2, 3]
        assert [i.ingredient_id for i in session.ingredients] == ["flour", "sugar"]
        assert session.current_step_number == 1
        assert session.status is PreparationStatus.IN_PROGRESS

    def test_recipe_without_steps_has_no_current_step(self):
        assert PreparationSession.start(ME, make_recipe(steps=0)).current_step_number is None

    def test_completing_current_step_moves_to_next_pending(self):
        session = PreparationSession.start(ME, make_recipe())

        session.complete_step(1, NOW)

        assert session.current_step_number == 2
        assert session.completed_steps == 1

    def test_next_pending_wraps_around_and_skips_completed(self):
        session = PreparationSession.start(ME, make_recipe())
        session.complete_step(2, NOW)  # not the current one: current stays
        assert session.current_step_number == 1

        session.go_to_step(3)
        session.complete_step(3, NOW)

        assert session.current_step_number == 1

    def test_all_done_stays_on_last_completed(self):
        session = PreparationSession.start(ME, make_recipe())
        for n in (1, 2, 3):
            session.complete_step(n, NOW)
        assert session.current_step_number == 3

    def test_completing_twice_keeps_first_timestamp(self):
        session = PreparationSession.start(ME, make_recipe())
        session.complete_step(1, NOW)
        session.complete_step(1, NOW + timedelta(minutes=5))
        assert session.steps[0].completed_at == NOW

    def test_uncomplete(self):
        session = PreparationSession.start(ME, make_recipe())
        session.complete_step(1, NOW)
        session.uncomplete_step(1)
        assert session.completed_steps == 0

    def test_unknown_step(self):
        session = PreparationSession.start(ME, make_recipe())
        with pytest.raises(PreparationStepNotFoundError):
            session.go_to_step(99)

    def test_timer(self):
        session = PreparationSession.start(ME, make_recipe(timer_on=2))
        step = session.steps[1]
        assert step.timer_remaining_seconds(NOW) is None

        session.start_timer(2, NOW)

        assert step.timer_remaining_seconds(NOW + timedelta(seconds=100)) == 500
        assert step.timer_remaining_seconds(NOW + timedelta(hours=1)) == 0

    def test_restarting_timer_resets_it(self):
        session = PreparationSession.start(ME, make_recipe(timer_on=2))
        session.start_timer(2, NOW)
        session.start_timer(2, NOW + timedelta(seconds=300))
        assert session.steps[1].timer_remaining_seconds(NOW + timedelta(seconds=300)) == 600

    def test_timer_on_step_without_timer(self):
        session = PreparationSession.start(ME, make_recipe(timer_on=2))
        with pytest.raises(StepHasNoTimerError):
            session.start_timer(1, NOW)

    @pytest.mark.parametrize("end", ["finish", "abandon"])
    def test_finished_preparation_is_read_only(self, end):
        session = PreparationSession.start(ME, make_recipe())
        getattr(session, end)(NOW)

        assert session.finished_at == NOW
        assert session.status is (PreparationStatus.COMPLETED if end == "finish" else PreparationStatus.ABANDONED)
        for command in (
            lambda: session.complete_step(1, NOW),
            lambda: session.go_to_step(1),
            lambda: session.start_timer(2, NOW),
            lambda: session.finish(NOW),
            lambda: session.abandon(NOW),
        ):
            with pytest.raises(PreparationNotInProgressError):
                command()


@pytest.fixture
def repo():
    return InMemoryPreparationRepository()


@pytest.fixture
def display():
    return FakeQuantityDisplay()


@pytest.fixture
def assembler(display):
    return PreparationAssembler(display)


@pytest.fixture
def start(repo, assembler):
    return StartPreparationUseCase(repo, FakeRecipeSource(make_recipe("r1"), make_recipe("r2")), assembler)


class TestUseCases:

    async def test_start_then_resume(self, start, repo):
        first = await start.execute(ME, "r1", "metric")
        again = await start.execute(ME, "r1", "metric")

        assert first.resumed is False
        assert again.resumed is True
        assert again.preparation.id == first.preparation.id
        assert len(repo.items) == 1

    async def test_new_preparation_after_finishing(self, start, repo, assembler):
        first = await start.execute(ME, "r1", "metric")
        await PreparationProgressUseCases(repo, assembler).finish(ME, first.preparation.id, "metric")

        second = await start.execute(ME, "r1", "metric")

        assert second.resumed is False
        assert second.preparation.id != first.preparation.id

    async def test_start_unknown_recipe(self, start):
        with pytest.raises(PreparationRecipeNotFoundError):
            await start.execute(ME, "missing", "metric")

    async def test_quantities_in_unit_system(self, start, display):
        detail = (await start.execute(ME, "r1", "metric")).preparation

        flour = detail.ingredients[0]
        assert (flour.quantity, flour.unit_abbreviation, flour.converted) == (Decimal("200"), "g", True)
        assert (flour.original_quantity, flour.original_unit_abbreviation) == (Decimal("2"), "cup")

    async def test_original_units_skip_conversion(self, start, display):
        detail = (await start.execute(ME, "r1", "original")).preparation

        assert display.calls == 0
        assert (detail.ingredients[0].quantity, detail.ingredients[0].unit_abbreviation) == (Decimal("2"), "cup")
        assert detail.ingredients[0].converted is False

    async def test_detail_marks_current_step(self, start):
        detail = (await start.execute(ME, "r1", "original")).preparation
        assert [s.is_current for s in detail.steps] == [True, False, False]
        assert (detail.completed_steps, detail.total_steps) == (0, 3)

    @pytest.mark.parametrize("raw", ["garbage", None])
    async def test_other_users_preparation_is_not_found(self, start, repo, assembler, raw):
        mine = (await start.execute(ME, "r1", "original")).preparation
        target = raw or mine.id

        with pytest.raises(PreparationNotFoundError):
            await GetPreparationUseCase(repo, assembler).execute("intruder", target, "original")

    async def test_progress_commands(self, start, repo, assembler):
        prep_id = (await start.execute(ME, "r1", "original")).preparation.id
        progress = PreparationProgressUseCases(repo, assembler)

        detail = await progress.complete_step(ME, prep_id, 1, "original")
        assert detail.current_step_number == 2

        detail = await progress.start_timer(ME, prep_id, 2, "original")
        assert detail.steps[1].timer_remaining_seconds == 600

        detail = await progress.uncomplete_step(ME, prep_id, 1, "original")
        assert detail.completed_steps == 0

        detail = await progress.go_to_step(ME, prep_id, 3, "original")
        assert detail.current_step_number == 3

        detail = await progress.abandon(ME, prep_id, "original")
        assert detail.status == "abandoned"

    async def test_history(self, start, repo, assembler):
        a = (await start.execute(ME, "r1", "original")).preparation
        await start.execute(ME, "r2", "original")
        await PreparationProgressUseCases(repo, assembler).finish(ME, a.id, "original")
        await StartPreparationUseCase(repo, FakeRecipeSource(make_recipe("r1")), assembler).execute(
            "other", "r1", "original"
        )
        history = ListPreparationsUseCase(repo)

        everything = await history.execute(ME, None, None, 10, 0)
        completed = await history.execute(ME, "completed", None, 10, 0)
        of_r2 = await history.execute(ME, None, "r2", 10, 0)

        assert everything.total == 2
        assert [p.id for p in completed.items] == [a.id]
        assert [p.recipe_id for p in of_r2.items] == ["r2"]
