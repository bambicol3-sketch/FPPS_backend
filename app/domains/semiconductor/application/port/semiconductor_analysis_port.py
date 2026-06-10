from abc import ABC, abstractmethod

from app.domains.semiconductor.domain.entity.semiconductor_analysis import SemiconductorAnalysis


class SemiconductorAnalysisPort(ABC):
    @abstractmethod
    async def analyze(self, ticker: str, query: str) -> SemiconductorAnalysis:
        ...
