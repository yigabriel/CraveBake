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

Synonyms: a name may list regional words for the same thing, separated by " / "
("Mantequilla / Manteca"). Searching finds it by any of them (it is a plain
substring), and `matches_name` treats each one as the name too, so typing
"manteca" is recognised as the existing ingredient instead of a new one.
"""
from __future__ import annotations

from typing import Any

from sqlalchemy import func, or_

from app.shared.domain.text_folding import ACCENTED as _ACCENTED
from app.shared.domain.text_folding import PLAIN as _PLAIN
from app.shared.domain.text_folding import SYNONYM_SEPARATOR, fold


def folded(column: Any):
    """SQL expression: `column` folded like `fold()` does."""
    return func.lower(func.translate(column, _ACCENTED, _PLAIN))


def _escape_like(text: str) -> str:
    # A typed "100%" or "a_b" must match literally, not act as a wildcard.
    return text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def equals_folded(column: Any, text: str):
    """WHERE clause: `column` equals `text`, ignoring case and accents."""
    return folded(column) == fold(text)


def matches_name(column: Any, text: str):
    """WHERE clause: `text` is the name in `column` or one of its " / "-separated synonyms.

    Ignores case and accents. "manteca" matches "Mantequilla / Manteca", but "mantequilla"
    does not match "Mantequilla de maní": a synonym is a whole word group, not a prefix.
    """
    wanted = _escape_like(fold(text))
    folded_column = folded(column)
    separator = _escape_like(SYNONYM_SEPARATOR)
    return or_(
        folded_column == fold(text),
        folded_column.like(f"{wanted}{separator}%", escape="\\"),
        folded_column.like(f"%{separator}{wanted}", escape="\\"),
        folded_column.like(f"%{separator}{wanted}{separator}%", escape="\\"),
    )


def contains_folded(column: Any, text: str):
    """WHERE clause: `text` appears in `column`, ignoring case and accents."""
    return folded(column).like(f"%{_escape_like(fold(text))}%", escape="\\")
