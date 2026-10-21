import pytest

from app.shared.database.text_search import _ACCENTED, _PLAIN, fold


class TestFold:

    @pytest.mark.parametrize(
        "typed, expected",
        [
            ("Azúcar", "azucar"),
            ("  AZÚCAR  ", "azucar"),
            ("Crème brûlée", "creme brulee"),
            ("Piña colada", "pina colada"),
            ("ÁÉÍÓÚ ÑANDÚ", "aeiou nandu"),
            ("Butter", "butter"),
        ],
    )
    def test_removes_accents_and_case(self, typed, expected):
        assert fold(typed) == expected

    def test_both_spellings_fold_to_the_same_text(self):
        assert fold("azucar") == fold("Azúcar") == fold("AZÚCAR")

    def test_the_character_table_is_consistent(self):
        # translate() needs one replacement per accented character: a typo here would shift them all.
        assert len(_ACCENTED) == len(_PLAIN)
