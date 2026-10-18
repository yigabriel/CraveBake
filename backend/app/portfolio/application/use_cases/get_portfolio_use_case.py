"""
GetPortfolioUseCase — "Mi Portafolio": original, personalized and saved recipes in one list.

Newest first. `kind` narrows it to one section (e.g. 'saved' is the
favorites screen), `query` filters by title, `category_id` by recipe
category and `tag_ids` by tags (the recipe must have all of them). Unknown
or malformed filter ids simply match nothing. `total` is the count after
filtering, before pagination, so the client can paginate.
"""
from __future__ import annotations

from app.portfolio.application.dto.portfolio_dto import GetPortfolioDTO, PortfolioItemDTO
from app.portfolio.application.use_cases.portfolio_reader import PortfolioReader, entry_to_dto
from app.portfolio.domain.entities.portfolio_entry import PortfolioItemKind
from app.shared.application.pagination import Page
from app.shared.domain.value_objects.entity_id import EntityId


class GetPortfolioUseCase:
    def __init__(self, portfolio_reader: PortfolioReader) -> None:
        self._portfolio_reader = portfolio_reader

    async def execute(self, dto: GetPortfolioDTO) -> Page[PortfolioItemDTO]:
        entries = await self._portfolio_reader.load(dto.user_id)

        if dto.kind is not None:
            kind = PortfolioItemKind(dto.kind)
            entries = [entry for entry in entries if entry.kind == kind]
        if dto.category_id is not None or dto.tag_ids:
            category_id = _canonical(dto.category_id) if dto.category_id else None
            tag_ids = [_canonical(raw) for raw in dto.tag_ids]
            entries = [entry for entry in entries if entry.recipe.matches(category_id, tag_ids)]
        if dto.query and dto.query.strip():
            needle = dto.query.strip().lower()
            entries = [entry for entry in entries if needle in entry.recipe.title.lower()]

        page = entries[dto.offset : dto.offset + dto.limit]
        return Page(
            items=[entry_to_dto(entry) for entry in page],
            total=len(entries),
            limit=dto.limit,
            offset=dto.offset,
        )


def _canonical(raw_id: str) -> str:
    parsed = EntityId.try_from_string(raw_id)
    return str(parsed) if parsed else raw_id
