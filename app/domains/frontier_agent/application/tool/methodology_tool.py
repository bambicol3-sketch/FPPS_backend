from datetime import datetime, timezone
from typing import List, Optional

from app.domains.ddakjubu2.application.port.methodology_repository_port import (
    MethodologyRepositoryPort,
)
from app.domains.frontier_agent.application.port.frontier_ports import FrontierToolPort
from app.domains.frontier_agent.domain.entity.analysis_run import ToolEvidence


class MethodologyTool(FrontierToolPort):
    """딱주부TV 방송에서 학습한 종합 분석 방법론을 분석 프레임으로 제공하는 도구."""

    name = "methodology"
    description = "딱주부TV 학습 종합 방법론(분석 단계·지표·판단 규칙)"

    def __init__(self, methodology_repository_port: MethodologyRepositoryPort):
        self._methodology_repository_port = methodology_repository_port

    def applies(self, question: str, ticker: Optional[str]) -> bool:
        return True

    async def gather(
        self, question: str, ticker: Optional[str], stock_name: Optional[str]
    ) -> List[ToolEvidence]:
        master = await self._methodology_repository_port.find_latest_master()
        if master is None:
            return [
                ToolEvidence(
                    tool=self.name,
                    source_institution="딱주부TV 학습 방법론",
                    data_origin="방송 학습 노트",
                    collected_by="자체 LLM 추출",
                    publish_method="누적 학습",
                    content="종합 방법론이 아직 생성되지 않았습니다.",
                    available=False,
                    retrieved_at=datetime.now(timezone.utc),
                )
            ]
        methodology, version = master
        lines = [f"종합 방법론(v{version}): {methodology.methodology_name}"]
        for step in methodology.analysis_steps:
            lines.append(f"- {step.step_order}. {step.name}: {step.description}")
            if step.decision_rules:
                lines.append(f"    규칙: {'; '.join(step.decision_rules)}")
        if methodology.risk_management:
            lines.append(f"- 리스크 관리: {'; '.join(methodology.risk_management)}")
        return [
            ToolEvidence(
                tool=self.name,
                source_institution="딱주부TV 학습 방법론",
                data_origin="방송 학습 노트에서 역설계한 분석 절차",
                collected_by="자체 LLM 추출·주간 병합",
                publish_method="마스터 방법론 버전",
                content="\n".join(lines),
                available=True,
                retrieved_at=datetime.now(timezone.utc),
            )
        ]
