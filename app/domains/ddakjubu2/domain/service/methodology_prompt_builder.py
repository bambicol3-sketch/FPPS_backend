from app.domains.ddakjubu2.domain.entity.learning_note import LearningNote
from app.domains.ddakjubu2.domain.entity.source_video import SourceVideo

TRANSCRIPT_MAX_CHARS = 30000


class MethodologyPromptBuilder:
    """영상에서 '재사용 가능한 분석 방법론'을 역설계하는 3차 패스 프롬프트 빌더."""

    SYSTEM_INSTRUCTIONS = (
        "너는 주식 방송의 '분석 방법론'을 역설계하는 금융 교육 전문가다. "
        "주어진 딱주부TV 영상 컨텍스트(핵심 요약, 종목 인사이트, 제목, 설명, 자막)에서 "
        "진행자가 종목·시장을 분석할 때 사용하는 '재사용 가능한 방법론'을 추출한다. "
        "결론(강세/약세)이 아니라 결론에 도달하는 절차를 추출하라: "
        "(1) 어떤 지표/데이터를 어떤 순서로 확인하는가 (예: 수급, 데드라인, 밴드, 거래량, 재무, 금리), "
        "(2) 각 단계에서 어떤 판단 규칙(임계값, 조건)을 적용하는가, "
        "(3) 리스크 관리 원칙 (손절 기준, 비중 조절, 관망 전환 조건), "
        "(4) 이 방법이 유효한 시장 상황. "
        "영상에 명시적으로 드러난 방법만 추출하고, 일반론적 추측을 덧붙이지 않는다. "
        "분석 방법론이 드러나지 않는 영상이면 analysis_steps 를 빈 배열로 반환한다. "
        "반드시 지정된 JSON 스키마로만 응답한다."
    )

    JSON_SCHEMA_GUIDE = """반드시 다음 JSON 형식으로만 응답하라. 다른 설명 텍스트·코드펜스 절대 금지.

{
  "methodology_name": "이 방법론을 요약하는 이름 (예: 수급-데드라인 추세 점검법)",
  "analysis_steps": [
    {
      "step_order": 1,
      "name": "단계 이름 (예: 외국인/기관 수급 확인)",
      "description": "이 단계에서 무엇을 어떻게 확인하는지",
      "indicators": ["사용 지표/데이터 1", "사용 지표/데이터 2"],
      "decision_rules": ["판단 규칙 1 (임계값·조건 포함)", "판단 규칙 2"]
    }
  ],
  "indicators_used": ["영상 전체에서 사용된 지표/데이터 목록"],
  "decision_rules": ["영상 전체에서 언급된 핵심 판단 규칙 목록"],
  "risk_management": ["리스크 관리 원칙 (없으면 빈 배열)"],
  "applicable_market_conditions": "이 방법론이 유효한 시장 상황 (없으면 빈 문자열)",
  "example_stocks": [
    {"stock_name": "영상에서 이 방법으로 분석한 종목명", "ticker": "종목 코드 (없으면 빈 문자열)", "applied_view": "강세 | 약세 | 중립 | 관망"}
  ]
}
"""

    def build(self, source_video: SourceVideo, note: LearningNote) -> str:
        summary_section = note.summary.strip() or "(핵심 요약 없음)"

        insight_lines = []
        for insight in note.stock_insights:
            insight_lines.append(
                f"- {insight.stock_name}"
                + (f" ({insight.ticker})" if insight.ticker else "")
                + f": {insight.investment_view or '-'}"
            )
            for claim in insight.key_claims:
                insight_lines.append(f"  - 주장: {claim}")
        insight_section = "\n".join(insight_lines) or "(종목 인사이트 없음)"

        transcript = source_video.transcript or ""
        if len(transcript) > TRANSCRIPT_MAX_CHARS:
            transcript = transcript[:TRANSCRIPT_MAX_CHARS] + "\n...(이하 생략)"
        transcript_section = transcript or "(자막/음성 변환 텍스트 제공되지 않음)"

        return (
            "다음은 딱주부TV 영상 데이터와 이전 패스에서 추출된 결과다.\n\n"
            f"[영상 ID] {source_video.video_id}\n"
            f"[업로드 일시] {source_video.published_at.isoformat()}\n"
            f"[제목]\n{source_video.title}\n\n"
            f"[설명]\n{source_video.description}\n\n"
            f"[핵심 요약]\n{summary_section}\n\n"
            f"[종목별 인사이트]\n{insight_section}\n\n"
            f"[자막/음성 변환]\n{transcript_section}\n\n"
            "위 컨텍스트에서 진행자의 재사용 가능한 분석 방법론을 역설계하라.\n\n"
            f"{self.JSON_SCHEMA_GUIDE}"
        )
