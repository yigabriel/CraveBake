"""GetPortfolioSummaryUseCase — how many recipes the user has in each portfolio section."""
from __future__ import annotations

from collections import Counter

from app.portfolio.application.dto.portfolio_dto import PortfolioSummaryDTO
from app.portfolio.application.use_cases.portfolio_reader import PortfolioReader
from app.portfolio.domain.entities.portfolio_entry import PortfolioItemKind


class GetPortfolioSummaryUseCase:
    def __init__(self, portfolio_reader: PortfolioReader) -> None:
        self._portfolio_reader = portfolio_reader

    async def execute(self, user_id: str) -> PortfolioSummaryDTO:
        entries = await self._portfolio_reader.load(user_id)
        counts = Counter(entry.kind for entry in entries)
        return PortfolioSummaryDTO(
            original_count=counts[PortfolioItemKind.ORIGINAL],
            personalized_count=counts[PortfolioItemKind.PERSONALIZED],
            saved_count=counts[PortfolioItemKind.SAVED],
            total=len(entries),
        )
