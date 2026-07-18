from typing import List

from app.domains.ddakjubu2.domain.entity.analysis_methodology import AnalysisMethodology

MERGE_INPUT_MAX_CHARS = 24000


class MethodologyMergePromptBuilder:
    """여러 영상의 방법론을 하나의 마스터 프로파일로 통합하는 프롬프트 빌더."""

    SYSTEM_INSTRUCTIONS = (
        "너는 여러 방송에서 추출된 주식 분석 방법론들을 하나의 '종합 방법론 프로파일'로 "
        "통합하는 전문가다. "
        "반복적으로 등장하는 단계/지표/규칙을 우선 채택하고, 1회성 언급은 제외하거나 "
        "risk_management·decision_rules 의 비고 수준으로만 반영한다. "
        "상충하는 규칙이 있으면 더 최근 방송(목록 앞쪽)의 규칙을 우선한다. "
        "단계 수는 4~8개로 정리하고, 각 단계는 실행 순서대로 배열한다. "
        "반드시 지정된 JSON 스키마로만 응답한다."
    )

    JSON_SCHEMA_GUIDE = """반드시 다음 JSON 형식으로만 응답하라. 다른 설명 텍스트·코드펜스 절대 금지.

{
  "methodology_name": "종합 방법론 이름",
  "analysis_steps": [
    {
      "step_order": 1,
      "name": "단계 이름",
      "description": "이 단계에서 무엇을 어떻게 확인하는지",
      "indicators": ["사용 지표/데이터"],
      "decision_rules": ["판단 규칙 (임계값·조건 포함)"]
    }
  ],
  "indicators_used": ["전체 지표/데이터 목록"],
  "decision_rules": ["핵심 판단 규칙 목록"],
  "risk_management": ["리스크 관리 원칙"],
  "applicable_market_conditions": "유효한 시장 상황",
  "example_stocks": []
}
"""

    def build(self, methodologies: List[AnalysisMethodology]) -> str:
        blocks: List[str] = []
        total = 0
        included = 0
        for m in methodologies:  # 호출부에서 최신순으로 전달
            block = self._format_methodology(m)
            if total + len(block) > MERGE_INPUT_MAX_CHARS:
                break
            blocks.append(block)
            total += len(block)
            included += 1

        body = "\n\n".join(blocks) or "(방법론 없음)"
        return (
            "다음은 딱주부TV 개별 방송에서 추출된 분석 방법론 목록이다. "
            "최신 방송이 앞에 온다.\n\n"
            f"{body}\n\n"
            f"위 {included}개 방법론을 하나의 종합 방법론 프로파일로 통합하라.\n\n"
            f"{self.JSON_SCHEMA_GUIDE}"
        )

    @staticmethod
    def _format_methodology(m: AnalysisMethodology) -> str:
        lines = [
            f"### [{m.video_id}] {m.video_title}",
            f"- 방법론: {m.methodology_name or '-'}",
        ]
        for step in m.analysis_steps:
            lines.append(f"- 단계 {step.step_order}. {step.name}: {step.description}")
            if step.indicators:
                lines.append(f"  - 지표: {', '.join(step.indicators)}")
            for rule in step.decision_rules:
                lines.append(f"  - 규칙: {rule}")
        if m.risk_management:
            lines.append(f"- 리스크 관리: {'; '.join(m.risk_management)}")
        if m.applicable_market_conditions:
            lines.append(f"- 유효 시장 상황: {m.applicable_market_conditions}")
        return "\n".join(lines)
