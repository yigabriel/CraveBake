"""
Generic UUID-based identifier.

Every bounded context that needs a typed entity id (IngredientId, UnitId,
etc.) subclasses this instead of re-writing the same UUID wrapper. Keeping
each id as its own subclass (not a bare UUID) still gives type-safety —
`IngredientId` and `UnitId` are not interchangeable even though both wrap
a UUID — while avoiding boilerplate duplication across 
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field


@dataclass(frozen=True)
class EntityId:
    value: uuid.UUID = field(default_factory=uuid.uuid4)

    @classmethod
    def from_string(cls, raw: str) -> "EntityId":
        return cls(uuid.UUID(raw))

    @classmethod
    def try_from_string(cls, raw: str):
        """Like `from_string`, but returns None for a malformed id instead of raising.

        Lets use cases turn a garbage path parameter into a clean 404 rather
        than a 500 from `uuid.UUID`.
        """
        try:
            return cls(uuid.UUID(raw))
        except (ValueError, TypeError, AttributeError):
            return None

    def __str__(self) -> str:
        return str(self.value)
