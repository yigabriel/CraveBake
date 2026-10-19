"""Domain services: MeasurementConverter (tool) and UnitSystemConverter (display)."""
from decimal import Decimal

import pytest

from app.ingredients.domain.entities.ingredient import Ingredient
from app.ingredients.domain.entities.unit import UnitSystem
from app.ingredients.domain.exceptions import ConversionNotAvailableError
from app.ingredients.domain.services.measurement_converter import MeasurementConverter
from app.ingredients.domain.services.unit_system_converter import UnitSystemConverter
from tests.ingredients.fakes import conversion, seed_units

D = Decimal


@pytest.fixture
def units():
    return seed_units()


@pytest.fixture
def flour():
    return Ingredient.create("Harina todo uso (0000)")


class TestMeasurementConverter:

    def test_same_unit_is_identity(self, units):
        assert MeasurementConverter().convert(D("3"), units["g"], units["g"]) == D("3")

    def test_weight_to_weight(self, units):
        assert MeasurementConverter().convert(D("1.5"), units["kg"], units["g"]) == D("1500")

    def test_volume_to_volume(self, units):
        result = MeasurementConverter().convert(D("1"), units["cup"], units["tbsp"])
        assert round(result, 2) == D("16.00")

    def test_volume_to_weight_uses_ingredient_ratio(self, units, flour):
        cup_of_flour = conversion(flour, units["cup"], "125")

        result = MeasurementConverter().convert(D("2"), units["cup"], units["g"], cup_of_flour)

        assert result == D("250")

    def test_weight_to_volume_uses_ingredient_ratio(self, units, flour):
        cup_of_flour = conversion(flour, units["cup"], "125")

        result = MeasurementConverter().convert(D("250"), units["g"], units["cup"], cup_of_flour)

        assert result == D("2")

    def test_ratio_of_the_volume_unit_in_use(self, units, flour):
        # Contract: the ratio is for the volume unit being converted (the use case looks it up that way).
        tbsp_of_flour = conversion(flour, units["tbsp"], "8")

        result = MeasurementConverter().convert(D("100"), units["g"], units["tbsp"], tbsp_of_flour)

        assert result == D("12.5")

    def test_ratio_of_another_measure_via_conversion_unit(self, units, flour):
        cup_of_flour = conversion(flour, units["cup"], "125")

        result = MeasurementConverter().convert(
            D("236.588"), units["ml"], units["g"], cup_of_flour, conversion_unit=units["cup"]
        )

        assert result == D("125")

    def test_ratio_read_against_wrong_unit_fails_loudly(self, units, flour):
        cup_of_flour = conversion(flour, units["cup"], "125")
        with pytest.raises(ValueError):
            MeasurementConverter().convert(D("1"), units["ml"], units["g"], cup_of_flour)

    def test_across_types_without_ratio_fails(self, units):
        with pytest.raises(ConversionNotAvailableError):
            MeasurementConverter().convert(D("1"), units["cup"], units["g"])

    @pytest.mark.parametrize("pair", [("u", "g"), ("cup", "u")])
    def test_count_units_never_convert(self, units, flour, pair):
        ratio = conversion(flour, units["cup"], "125")
        with pytest.raises(ConversionNotAvailableError):
            MeasurementConverter().convert(D("1"), units[pair[0]], units[pair[1]], ratio)


class TestUnitSystemConverter:

    def _show(self, units, quantity, abbreviation, target, grams_per_unit=None):
        return UnitSystemConverter().to_system(
            D(quantity), units[abbreviation], target, units, grams_per_unit or {}
        )

    def test_already_in_target_system_is_untouched(self, units):
        shown = self._show(units, "250", "g", UnitSystem.METRIC)
        assert (shown.quantity, shown.unit.abbreviation, shown.converted) == (D("250"), "g", False)

    def test_count_units_are_untouched(self, units):
        shown = self._show(units, "3", "u", UnitSystem.US)
        assert (shown.unit.abbreviation, shown.converted) == ("u", False)

    def test_us_cup_of_flour_becomes_grams(self, units):
        shown = self._show(units, "1", "cup", UnitSystem.METRIC, {units["cup"].id: D("125")})
        assert (shown.quantity, shown.unit.abbreviation) == (D("125"), "g")

    def test_us_volume_without_weight_becomes_ml(self, units):
        shown = self._show(units, "1", "cup", UnitSystem.METRIC)
        assert (shown.quantity, shown.unit.abbreviation) == (D("237"), "ml")

    def test_big_amounts_use_kg_and_l(self, units):
        assert self._show(units, "4", "cup", UnitSystem.METRIC).unit.abbreviation == "ml"  # 946 ml
        shown = self._show(units, "5", "cup", UnitSystem.METRIC)
        assert (shown.quantity, shown.unit.abbreviation) == (D("1.18"), "l")
        shown = self._show(units, "40", "oz", UnitSystem.METRIC)
        assert (shown.quantity, shown.unit.abbreviation) == (D("1.13"), "kg")

    def test_small_metric_amounts_keep_one_decimal(self, units):
        shown = self._show(units, "1", "tsp", UnitSystem.METRIC)
        assert (shown.quantity, shown.unit.abbreviation) == (D("4.9"), "ml")

    @pytest.mark.parametrize(
        "ml, expected",
        [("240", (D("1.01"), "cup")), ("60", (D("0.25"), "cup")), ("30", (D("2.03"), "tbsp")), ("5", (D("1.01"), "tsp"))],
    )
    def test_metric_volume_picks_natural_us_measure(self, units, ml, expected):
        shown = self._show(units, ml, "ml", UnitSystem.US)
        assert (shown.quantity, shown.unit.abbreviation) == expected

    def test_tiny_amounts_never_round_to_zero(self, units):
        shown = self._show(units, "0.1", "ml", UnitSystem.US)
        assert (shown.quantity, shown.unit.abbreviation) == (D("0.125"), "tsp")

    def test_cups_keep_precision_for_the_client_to_round(self, units):
        # 100 g of flour is 0.8 cup: rounding to a quarter here (0.75) would lose 6 g before scaling.
        shown = self._show(units, "100", "g", UnitSystem.US, {units["cup"].id: D("125")})
        assert (shown.quantity, shown.unit.abbreviation) == (D("0.80"), "cup")

    def test_grams_with_volume_figure_become_cups(self, units):
        shown = self._show(units, "250", "g", UnitSystem.US, {units["cup"].id: D("125")})
        assert (shown.quantity, shown.unit.abbreviation) == (D("2.00"), "cup")

    def test_grams_prefer_figure_of_exact_measure(self, units):
        # Butter-like case: tbsp figure is not cup/16, so the tbsp figure must be used.
        figures = {units["cup"].id: D("227"), units["tbsp"].id: D("10")}
        shown = self._show(units, "30", "g", UnitSystem.US, figures)
        assert (shown.quantity, shown.unit.abbreviation) == (D("3.00"), "tbsp")

    def test_grams_without_volume_figure_become_ounces(self, units):
        shown = self._show(units, "100", "g", UnitSystem.US)
        assert (shown.quantity, shown.unit.abbreviation) == (D("3.5"), "oz")
