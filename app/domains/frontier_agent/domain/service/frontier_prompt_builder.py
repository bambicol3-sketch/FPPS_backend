from typing import List, Optional

from app.domains.frontier_agent.domain.entity.analysis_run import ToolEvidence


class FrontierPromptBuilder:
    """프론티어 에이전트 각 노드의 프롬프트 빌더 (순수 도메인 서비스).

    provenance-aware: 근거는 출처 메타와 함께 제시하고, Analyst 는 주장마다 [출처] 를
    인용하며 제공되지 않은 데이터는 추측 금지·판단 보류하도록 강제한다.
    read-only·조언용: 매매 지시가 아니라 분석·시나리오만.
    """

    PLANNER_SYSTEM = (
        "너는 한국 주식/시장 분석 에이전트의 Planner 다. 사용자 질문을 3단계 이내의 "
        "한국어 분석 계획으로 분해한다. 각 단계는 '어떤 데이터를 확인해 무엇을 판단할지'를 "
        "한 줄로, 숫자 접두어(1., 2., 3.)로 쓴다. 사용 가능한 도구 목록을 참고하되 없는 "
        "데이터에 의존하는 계획은 세우지 않는다."
    )

    ANALYST_SYSTEM = (
        "너는 Analyst 다. 아래 [근거]에 실제로 제공된 데이터만 사용해 사용자 질문에 답한다. "
        "규칙:\n"
        "1. 각 주장 끝에 근거 출처를 [출처: 기관명] 형태로 인용한다.\n"
        "2. 근거에 없는 값은 추측하지 말고 '데이터 미제공'으로 명시하고 판단을 보류한다.\n"
        "3. 매매 실행 지시(사라/팔아라)가 아니라 관점·시나리오·체크포인트로 서술한다.\n"
        "4. 한국어 4~7문장. 마지막에 핵심 관점 한 줄 요약."
    )

    REVIEWER_SYSTEM = (
        "너는 Reviewer 다. Analyst 분석이 (a) 근거 없는 주장을 하지 않았는지, "
        "(b) 데이터 공백을 정직하게 밝혔는지, (c) 과신하지 않았는지 검토한다. "
        "문제가 있으면 'REVISE: <사유>' 한 줄로 시작하고, 충분하면 'OK' 한 줄로 시작한 뒤 "
        "그 아래에 사용자에게 전달할 최종 답변(한국어 3~6문장, 투자 권유가 아님을 명시)을 작성한다."
    )

    def build_planner(
        self, question: str, ticker: Optional[str], tool_names: List[str]
    ) -> str:
        target = f"[대상 종목] {ticker}\n" if ticker else ""
        return (
            f"[질문]\n{question}\n{target}\n"
            f"[사용 가능한 데이터 도구]\n- " + "\n- ".join(tool_names) + "\n\n"
            "위 도구로 확인 가능한 것 위주로 3단계 이내 분석 계획을 세워라."
        )

    def build_analyst(
        self,
        question: str,
        evidences: List[ToolEvidence],
        feedback: str = "",
    ) -> str:
        feedback_section = (
            f"\n[직전 검토 피드백 — 반영할 것]\n{feedback}\n" if feedback else ""
        )
        return (
            f"[질문]\n{question}\n\n"
            f"[근거]\n{self._format_evidences(evidences)}\n"
            f"{feedback_section}\n"
            "위 근거만으로 분석을 작성하라. 주장마다 [출처] 를 붙이고, 없는 데이터는 판단 보류."
        )

    def build_reviewer(self, question: str, analysis: str) -> str:
        return (
            f"[질문]\n{question}\n\n"
            f"[Analyst 분석]\n{analysis}\n\n"
            "위 분석을 검토하고 규칙에 따라 REVISE 또는 OK + 최종 답변을 작성하라."
        )

    @staticmethod
    def _format_evidences(evidences: List[ToolEvidence]) -> str:
        if not evidences:
            return "(제공된 근거 없음)"
        blocks: List[str] = []
        for i, e in enumerate(evidences, start=1):
            if not e.available:
                blocks.append(
                    f"<근거 {i} | {e.source_institution} | 상태: 데이터 소스 미연결>\n"
                    f"{e.content}"
                )
            else:
                blocks.append(
                    f"<근거 {i} | 출처: {e.source_institution} | 원천: {e.data_origin} | "
                    f"수집·검증: {e.collected_by} | 공개: {e.publish_method}>\n{e.content}"
                )
        return "\n\n".join(blocks)
