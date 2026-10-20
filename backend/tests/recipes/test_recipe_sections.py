"""Sections: named groups of ingredient lines and steps ("Masa choux", "Manjar")."""
from decimal import Decimal

import pytest

from app.recipes.domain.entities.recipe import IngredientLine, Recipe, StepDraft
from app.recipes.domain.entities.recipe_section import MAX_SECTIONS, MAX_SECTION_NAME_LENGTH
from app.shared.exceptions.domain_exceptions import ValidationError


def line(ingredient: str, section: str | None = None) -> IngredientLine:
    return IngredientLine(ingredient, Decimal("1"), "g", section=section)


def names(recipe: Recipe) -> list[str]:
    return [section.name for section in recipe.sections]


def section_of(recipe: Recipe, line_index: int) -> str | None:
    wanted = recipe.ingredients[line_index].section_id
    return next((section.name for section in recipe.sections if section.id == wanted), None)


def make(**overrides) -> Recipe:
    return Recipe.create(created_by_user_id="author", title="Profiteroles", **overrides)


class TestGroupingIngredients:

    def test_lines_without_a_section_keep_working(self):
        recipe = make(ingredients=[line("flour"), line("egg")])

        assert recipe.sections == []
        assert [i.section_id for i in recipe.ingredients] == [None, None]

    def test_a_section_is_stored_once_for_all_its_lines(self):
        recipe = make(ingredients=[line("water", "Masa choux"), line("butter", "Masa choux"), line("milk", "Manjar")])

        assert names(recipe) == ["Masa choux", "Manjar"]
        assert recipe.ingredients[0].section_id == recipe.ingredients[1].section_id
        assert recipe.ingredients[1].section_id != recipe.ingredients[2].section_id

    def test_names_are_the_same_section_ignoring_case_and_spacing(self):
        recipe = make(ingredients=[line("water", "Masa choux"), line("butter", "  masa   CHOUX ")])

        assert names(recipe) == ["Masa choux"]

    def test_a_blank_name_means_no_section(self):
        recipe = make(ingredients=[line("flour", "   "), line("egg", "Masa")])

        assert [section_of(recipe, 0), section_of(recipe, 1)] == [None, "Masa"]

    def test_lines_without_section_go_first(self):
        recipe = make(ingredients=[line("salt"), line("water", "Masa")])
        assert names(recipe) == ["Masa"]

        with pytest.raises(ValidationError, match="before the sections"):
            make(ingredients=[line("water", "Masa"), line("salt")])

    def test_a_sections_lines_must_be_together(self):
        with pytest.raises(ValidationError, match="listed together"):
            make(ingredients=[line("a", "Masa"), line("b", "Manjar"), line("c", "Masa")])

    def test_name_length_and_section_count_are_limited(self):
        with pytest.raises(ValidationError):
            make(ingredients=[line("a", "x" * (MAX_SECTION_NAME_LENGTH + 1))])
        with pytest.raises(ValidationError):
            make(ingredients=[line(str(i), f"Group {i}") for i in range(MAX_SECTIONS + 1)])


class TestSectionsAreSharedAndDropped:

    def test_steps_reuse_the_ingredients_section(self):
        recipe = make(
            ingredients=[line("water", "Masa choux")],
            steps=[StepDraft("Hervir el agua", section="masa choux"), StepDraft("Armar", section="Montaje")],
        )

        assert names(recipe) == ["Masa choux", "Montaje"]
        assert recipe.steps[0].section_id == recipe.ingredients[0].section_id

    def test_a_section_disappears_when_no_line_uses_it(self):
        recipe = make(ingredients=[line("water", "Masa"), line("milk", "Manjar")])

        recipe.replace_ingredients([line("water", "Masa")])

        assert names(recipe) == ["Masa"]

    def test_a_section_used_only_by_steps_survives_replacing_the_ingredients(self):
        recipe = make(ingredients=[line("water", "Masa")], steps=[StepDraft("Hervir", section="Masa")])

        recipe.replace_ingredients([line("flour")])

        assert names(recipe) == ["Masa"]
        assert recipe.steps[0].section_id is not None

    def test_replacing_with_the_same_name_keeps_the_section_identity(self):
        recipe = make(ingredients=[line("water", "Masa")])
        before = recipe.sections[0].id

        recipe.replace_ingredients([line("water", "Masa"), line("flour", "Masa")])

        assert recipe.sections[0].id == before


class TestPersonalization:

    def test_the_copy_has_its_own_sections_on_its_own_lines(self):
        original = make(
            ingredients=[line("water", "Masa"), line("milk", "Manjar")],
            steps=[StepDraft("Hervir", section="Masa")],
        )

        copy = original.personalize("baker")

        assert names(copy) == ["Masa", "Manjar"]
        assert {s.id for s in copy.sections}.isdisjoint({s.id for s in original.sections})
        assert [section_of(copy, 0), section_of(copy, 1)] == ["Masa", "Manjar"]
        assert copy.steps[0].section_id == copy.ingredients[0].section_id

        copy.replace_ingredients([line("water")])
        assert names(original) == ["Masa", "Manjar"]  # the original is untouched
