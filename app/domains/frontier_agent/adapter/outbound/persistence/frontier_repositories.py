from datetime import datetime
from typing import Callable, List, Optional

from sqlalchemy import select

from app.domains.frontier_agent.application.port.frontier_ports import (
    FrontierAnalysisRepositoryPort,
    FrontierAuditRepositoryPort,
)
from app.domains.frontier_agent.domain.entity.analysis_run import (
    FrontierAnalysis,
    ReasoningStep,
    ToolEvidence,
)
from app.domains.frontier_agent.infrastructure.orm.frontier_orm import (
    FrontierAnalysisRunOrm,
    FrontierAuditLogOrm,
)
from app.infrastructure.database.database import AsyncSessionLocal


def _analysis_to_json(analysis: FrontierAnalysis) -> dict:
    return {
        "plan": analysis.plan,
        "steps": [
            {"node": s.node, "content": s.content, "attempt": s.attempt}
            for s in analysis.steps
        ],
        "evidences": [
            {
                "tool": e.tool,
                "source_institution": e.source_institution,
                "data_origin": e.data_origin,
                "collected_by": e.collected_by,
                "publish_method": e.publish_method,
                "content": e.content,
                "available": e.available,
            }
            for e in analysis.evidences
        ],
        "missing_data": analysis.missing_data,
        "caveats": analysis.caveats,
        "analyzed_at": analysis.analyzed_at.isoformat()
        if analysis.analyzed_at
        else None,
    }


def _json_to_analysis(row: FrontierAnalysisRunOrm) -> FrontierAnalysis:
    data = row.result or {}
    analyzed_at = None
    if data.get("analyzed_at"):
        try:
            analyzed_at = datetime.fromisoformat(data["analyzed_at"])
        except ValueError:
            analyzed_at = None
    return FrontierAnalysis(
        run_id=row.run_id,
        question=row.question,
        ticker=row.ticker,
        stock_name=row.stock_name,
        plan=data.get("plan", ""),
        answer=row.answer,
        confidence=row.confidence,
        steps=[
            ReasoningStep(
                node=s.get("node", ""),
                content=s.get("content", ""),
                attempt=int(s.get("attempt", 1)),
            )
            for s in data.get("steps", [])
        ],
        evidences=[
            ToolEvidence(
                tool=e.get("tool", ""),
                source_institution=e.get("source_institution", ""),
                data_origin=e.get("data_origin", ""),
                collected_by=e.get("collected_by", ""),
                publish_method=e.get("publish_method", ""),
                content=e.get("content", ""),
                available=bool(e.get("available", True)),
            )
            for e in data.get("evidences", [])
        ],
        missing_data=data.get("missing_data", []),
        caveats=data.get("caveats", []),
        revised_count=row.revised_count,
        refused=row.refused,
        analyzed_at=analyzed_at,
    )


class FrontierAnalysisRepositoryImpl(FrontierAnalysisRepositoryPort):
    def __init__(self, session_factory: Optional[Callable] = None):
        self._session_factory = session_factory or AsyncSessionLocal

    async def save(self, analysis: FrontierAnalysis) -> None:
        async with self._session_factory() as session:
            session.add(
                FrontierAnalysisRunOrm(
                    run_id=analysis.run_id,
                    question=analysis.question,
                    ticker=analysis.ticker,
                    stock_name=analysis.stock_name,
                    answer=analysis.answer,
                    confidence=analysis.confidence,
                    result=_analysis_to_json(analysis),
                    revised_count=analysis.revised_count,
                    refused=analysis.refused,
                )
            )
            await session.commit()

    async def find_history(
        self, ticker: Optional[str], limit: int
    ) -> List[FrontierAnalysis]:
        async with self._session_factory() as session:
            stmt = select(FrontierAnalysisRunOrm)
            if ticker:
                stmt = stmt.where(FrontierAnalysisRunOrm.ticker == ticker)
            stmt = stmt.order_by(FrontierAnalysisRunOrm.created_at.desc()).limit(limit)
            rows = (await session.execute(stmt)).scalars().all()
            return [_json_to_analysis(r) for r in rows]


class FrontierAuditRepositoryImpl(FrontierAuditRepositoryPort):
    def __init__(self, session_factory: Optional[Callable] = None):
        self._session_factory = session_factory or AsyncSessionLocal

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
        async with self._session_factory() as session:
            session.add(
                FrontierAuditLogOrm(
                    run_id=run_id,
                    question=question,
                    ticker=ticker,
                    answer=answer,
                    confidence=confidence,
                    tools_used=tools_used,
                    revised_count=revised_count,
                    refused=refused,
                    latency_ms=latency_ms,
                )
            )
            await session.commit()

    async def find_recent(self, limit: int) -> List[dict]:
        async with self._session_factory() as session:
            stmt = (
                select(FrontierAuditLogOrm)
                .order_by(FrontierAuditLogOrm.created_at.desc())
                .limit(limit)
            )
            rows = (await session.execute(stmt)).scalars().all()
            return [
                {
                    "run_id": r.run_id,
                    "question": r.question,
                    "ticker": r.ticker,
                    "confidence": r.confidence,
                    "tools_used": r.tools_used,
                    "revised_count": r.revised_count,
                    "refused": r.refused,
                    "latency_ms": r.latency_ms,
                    "created_at": r.created_at,
                }
                for r in rows
            ]
