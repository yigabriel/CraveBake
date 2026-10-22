"""
Accent- and case-insensitive text comparison, as pure functions (no database).

"azucar" and "Azúcar" fold to the same word. The SQL side of the same rule lives
in `shared/database/text_search.py` and reads the same character table, so what the
application folds and what the database folds can never drift apart.

A name may list regional synonyms separated by " / " ("Mantequilla / Manteca").
"""
from __future__ import annotations

ACCENTED = "áàâäãåéèêëíìîïóòôöõúùûüñçÁÀÂÄÃÅÉÈÊËÍÌÎÏÓÒÔÖÕÚÙÛÜÑÇ"
PLAIN = "aaaaaaeeeeiiiiooooouuuuncaaaaaaeeeeiiiiooooouuuunc"
_TABLE = str.maketrans(ACCENTED, PLAIN)

SYNONYM_SEPARATOR = " / "


def fold(text: str) -> str:
    """"  Azúcar " -> "azucar": what two spellings of the same word have in common."""
    return text.strip().translate(_TABLE).lower()


def synonyms(name: str) -> list[str]:
    """"Mantequilla / Manteca" -> ["Mantequilla", "Manteca"]; a plain name is its own only word."""
    return [word.strip() for word in name.split(SYNONYM_SEPARATOR.strip()) if word.strip()]


def is_same_name(existing: str, typed: str) -> bool:
    """`typed` is `existing` or one of its synonyms, ignoring case and accents."""
    wanted = fold(typed)
    return fold(existing) == wanted or any(fold(word) == wanted for word in synonyms(existing))
