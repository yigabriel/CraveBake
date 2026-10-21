import pytest
from pydantic import BaseModel

from app.shared.domain.value_objects.localized_text import LocalizedText
from app.shared.exceptions.domain_exceptions import ValidationError
from app.shared.presentation.i18n import LocalizedStr


class TestLocalizedText:

    def test_falls_back_to_the_original_language(self):
        name = LocalizedText.of("Dulce de membrillo")
        assert (name.in_("en"), name.in_("es"), name.in_(None)) == ("Dulce de membrillo",) * 3

    def test_picks_the_requested_language(self):
        name = LocalizedText({"es": "Manteca", "en": "Butter"}, original="es")
        assert (name.in_("en"), name.in_("es"), name.text) == ("Butter", "Manteca", "Manteca")

    def test_cleans_texts_and_drops_empty_translations(self):
        name = LocalizedText({"es": "  Sal ", "en": "  "}, original="es")
        assert name.as_dict() == {"es": "Sal"}

    @pytest.mark.parametrize("values, original", [({}, "es"), ({"en": "Salt"}, "es"), ({"fr": "Sel"}, "fr")])
    def test_rejects_missing_original_or_unknown_language(self, values, original):
        with pytest.raises(ValidationError):
            LocalizedText(values, original=original)

    def test_is_immutable(self):
        name = LocalizedText.of("Sal")
        with pytest.raises(TypeError):
            name.values["en"] = "Salt"  # type: ignore[index]


class _Item(BaseModel):
    name: LocalizedStr
    note: LocalizedStr | None = None


class TestLocalizedStr:

    def test_picks_the_language_from_the_validation_context(self):
        item = _Item.model_validate({"name": LocalizedText({"es": "Manteca", "en": "Butter"}, original="es")}, context={"language": "en"})
        assert item.name == "Butter"

    def test_without_context_uses_the_original(self):
        assert _Item(name=LocalizedText({"es": "Manteca", "en": "Butter"}, original="es")).name == "Manteca"

    def test_plain_strings_and_none_pass_through(self):
        item = _Item.model_validate({"name": "Molde", "note": None}, context={"language": "en"})
        assert (item.name, item.note) == ("Molde", None)

    def test_optional_localized_values_are_localized_too(self):
        item = _Item.model_validate({"name": "x", "note": LocalizedText({"es": "Sal", "en": "Salt"}, original="es")}, context={"language": "en"})
        assert item.note == "Salt"


class TestWritten:

    def test_keeps_the_reviewed_translations(self):
        name = LocalizedText.written("Pistacho", "es", {"en": " Pistachio "})
        assert (name.in_("es"), name.in_("en"), name.original) == ("Pistacho", "Pistachio", "es")

    def test_a_blank_translation_means_not_translated(self):
        name = LocalizedText.written("Pistacho", "es", {"en": "   "})
        assert (name.in_("en"), tuple(name.values)) == ("Pistacho", ("es",))

    def test_the_written_language_cannot_also_be_a_translation(self):
        with pytest.raises(ValidationError):
            LocalizedText.written("Pistacho", "es", {"es": "Otro"})
