"""
Accent- and case-insensitive text matching, written once for every search.

"azucar" must find "Azúcar" and "MANTEQUILLA" must find "mantequilla": people
rarely type accents on a phone. Both sides are *folded* the same way — accents
removed, lowercase — and compared, so the database never needs an extension.

Folding is done with `translate()` (built into every PostgreSQL) instead of the
`unaccent` extension: nothing to install or migrate on each environment, and it
behaves the same whatever the database's locale (the accented capitals are mapped
explicitly, so it does not rely on `lower()` knowing about them).

Python (`fold`) and SQL (`folded`) share the same character table, so what the
application folds and what the database folds can never drift apart.
"""
from __future__ import annotations

from typing import Any

from sqlalchemy import func

_ACCENTED = "áàâäãåéèêëíìîïóòôöõúùûüñçÁÀÂÄÃÅÉÈÊËÍÌÎÏÓÒÔÖÕÚÙÛÜÑÇ"
_PLAIN = "aaaaaaeeeeiiiiooooouuuuncaaaaaaeeeeiiiiooooouuuunc"
_TABLE = str.maketrans(_ACCENTED, _PLAIN)


def fold(text: str) -> str:
    """"  Azúcar " -> "azucar": what two spellings of the same word have in common."""
    return text.strip().translate(_TABLE).lower()


def folded(column: Any):
    """SQL expression: `column` folded like `fold()` does."""
    return func.lower(func.translate(column, _ACCENTED, _PLAIN))


def _escape_like(text: str) -> str:
    # A typed "100%" or "a_b" must match literally, not act as a wildcard.
    return text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def equals_folded(column: Any, text: str):
    """WHERE clause: `column` equals `text`, ignoring case and accents."""
    return folded(column) == fold(text)


def contains_folded(column: Any, text: str):
    """WHERE clause: `text` appears in `column`, ignoring case and accents."""
    return folded(column).like(f"%{_escape_like(fold(text))}%", escape="\\")
