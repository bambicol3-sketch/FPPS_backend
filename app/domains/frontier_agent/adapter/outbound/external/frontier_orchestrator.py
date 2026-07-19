import uuid
from datetime import datetime, timezone
from typing import List, Optional

from app.domains.frontier_agent.application.port.frontier_ports import (
    FrontierLlmPort,
    FrontierToolPort,
)
from app.domains.frontier_agent.domain.entity.analysis_run import (
    FrontierAnalysis,
    ReasoningStep,
    ToolEvidence,
)
from app.domains.frontier_agent.domain.service.frontier_prompt_builder import (
    FrontierPromptBuilder,
)

REVISE_PREFIX = "REVISE"


class FrontierOrchestrator:
    """Planner → Researcher(도구 호출) → Analyst → Reviewer(REVISE 루프) 오케스트레이터.

    multi_agent 하네스와 동일한 흐름을 따르되, Researcher 가 순수 LLM 이 아니라
    실제 read-only 도구를 호출해 provenance 근거를 모은다.
    """

    def __init__(
        self,
        llm_port: FrontierLlmPort,
        tools: List[FrontierToolPort],
        max_revisions: int = 1,
    ):
        self._llm = llm_port
        self._tools = tools
        self._max_revisions = max_revisions
        self._prompt = FrontierPromptBuilder()

    async def run(
        self, question: str, ticker: Optional[str], stock_name: Optional[str]
    ) -> FrontierAnalysis:
        run_id = uuid.uuid4().hex
        steps: List[ReasoningStep] = []

        # 1) Planner
        applicable = [t for t in self._tools if t.applies(question, ticker)]
        plan = await self._llm.complete(
            FrontierPromptBuilder.PLANNER_SYSTEM,
            self._prompt.build_planner(
                question, ticker, [t.name for t in applicable]
            ),
        )
        steps.append(ReasoningStep(node="planner", content=plan))

        # 2) Researcher — 도구 호출로 근거 수집
        evidences: List[ToolEvidence] = []
        for tool in applicable:
            try:
                evidences.extend(
                    await tool.gather(question, ticker, stock_name)
                )
            except Exception as e:
                print(f"[frontier] 도구 {tool.name} 실패: {e}", flush=True)
        research_summary = self._summarize_research(evidences)
        steps.append(ReasoningStep(node="researcher", content=research_summary))

        available_evidences = [e for e in evidences if e.available]
        missing_data = [
            f"{e.source_institution}: {e.content[:60]}"
            for e in evidences
            if not e.available
        ]

        # 근거가 하나도 없으면(적용 도구 없음) 답변 거부 — 환각 방지
        if not evidences:
            return FrontierAnalysis(
                run_id=run_id,
                question=question,
                ticker=ticker,
                stock_name=stock_name,
                plan=plan,
                answer=(
                    "이 질문에 적용 가능한 데이터 도구가 없어 근거 기반 분석을 "
                    "제공할 수 없습니다. 종목을 지정하거나 질문을 구체화해 주세요."
                ),
                confidence=0,
                steps=steps,
                evidences=evidences,
                missing_data=missing_data,
                caveats=["근거 데이터 없음", "투자 권유가 아닙니다."],
                revised_count=0,
                refused=True,
                analyzed_at=datetime.now(timezone.utc),
            )

        # 3) Analyst + 4) Reviewer(REVISE 루프)
        feedback = ""
        revised_count = 0
        final_answer = ""
        for attempt in range(self._max_revisions + 1):
            analysis = await self._llm.complete(
                FrontierPromptBuilder.ANALYST_SYSTEM,
                self._prompt.build_analyst(question, evidences, feedback),
            )
            steps.append(
                ReasoningStep(node="analyst", content=analysis, attempt=attempt + 1)
            )

            review = await self._llm.complete(
                FrontierPromptBuilder.REVIEWER_SYSTEM,
                self._prompt.build_reviewer(question, analysis),
            )
            steps.append(
                ReasoningStep(node="reviewer", content=review, attempt=attempt + 1)
            )

            first_line, _, rest = review.partition("\n")
            head = first_line.strip()
            if head.upper().startswith(REVISE_PREFIX) and attempt < self._max_revisions:
                revised_count += 1
                feedback = head
                continue

            final_answer = self._extract_final_answer(head, rest, analysis)
            break

        confidence = self._estimate_confidence(available_evidences, missing_data)
        caveats = self._build_caveats(missing_data)

        return FrontierAnalysis(
            run_id=run_id,
            question=question,
            ticker=ticker,
            stock_name=stock_name,
            plan=plan,
            answer=final_answer,
            confidence=confidence,
            steps=steps,
            evidences=evidences,
            missing_data=missing_data,
            caveats=caveats,
            revised_count=revised_count,
            refused=False,
            analyzed_at=datetime.now(timezone.utc),
        )

    @staticmethod
    def _summarize_research(evidences: List[ToolEvidence]) -> str:
        if not evidences:
            return "적용 가능한 데이터 도구가 없어 근거를 수집하지 못했습니다."
        lines = []
        for e in evidences:
            status = "수집" if e.available else "미연결"
            lines.append(f"[{status}] {e.tool} ← {e.source_institution}")
        return "도구 호출 결과:\n" + "\n".join(lines)

    @staticmethod
    def _extract_final_answer(head: str, rest: str, fallback: str) -> str:
        if head.upper().startswith("OK"):
            head = head[2:].lstrip(":,.;-–— \t")
        combined = (head + ("\n" + rest if rest else "")).strip()
        return combined or fallback.strip()

    @staticmethod
    def _estimate_confidence(
        available: List[ToolEvidence], missing_data: List[str]
    ) -> int:
        if not available:
            return 0
        base = 40 + 15 * len(available)
        base -= 12 * len(missing_data)
        return max(10, min(85, base))

    @staticmethod
    def _build_caveats(missing_data: List[str]) -> List[str]:
        caveats = ["데이터는 조회 시점 기준입니다."]
        if missing_data:
            caveats.append(
                f"미연결 데이터 {len(missing_data)}건으로 일부 축의 판단을 보류했습니다."
            )
        caveats.append("본 분석은 방법론 기반 시뮬레이션이며 투자 권유가 아닙니다.")
        return caveats
