from abc import ABC, abstractmethod
from typing import List, Optional

from app.domains.frontier_agent.domain.entity.analysis_run import (
    FrontierAnalysis,
    ToolEvidence,
)


class FrontierLlmPort(ABC):
    """OpenAI 호환 chat 기반 LLM 포트 (base_url 교체로 온프레미스 서빙 호환)."""

    @abstractmethod
    async def complete(self, system_prompt: str, user_prompt: str) -> str:
        raise NotImplementedError


class FrontierToolPort(ABC):
    """read-only 데이터 도구. 결과는 provenance 메타를 포함한 ToolEvidence 로 반환한다."""

    name: str
    description: str

    @abstractmethod
    def applies(self, question: str, ticker: Optional[str]) -> bool:
        """이 질문/종목에 이 도구가 적용 가능한지."""
        raise NotImplementedError

    @abstractmethod
    async def gather(
        self, question: str, ticker: Optional[str], stock_name: Optional[str]
    ) -> List[ToolEvidence]:
        raise NotImplementedError


class FrontierAnalysisRepositoryPort(ABC):
    @abstractmethod
    async def save(self, analysis: FrontierAnalysis) -> None:
        raise NotImplementedError

    @abstractmethod
    async def find_history(
        self, ticker: Optional[str], limit: int
    ) -> List[FrontierAnalysis]:
        raise NotImplementedError


class FrontierAuditRepositoryPort(ABC):
    """불변 감사 로그 — 저장·조회만."""

    @abstractmethod
    async def save(
        self,
        run_id: str,
        question: str,
        ticker: Optional[str],
        answer: str,
        confidence: int,
        tools_used: List[str],
        revised_count: int,
        refused: bool,
        latency_ms: int,
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    async def find_recent(self, limit: int) -> List[dict]:
        raise NotImplementedError
