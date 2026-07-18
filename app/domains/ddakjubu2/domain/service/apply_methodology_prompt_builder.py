from app.domains.ddakjubu2.domain.entity.analysis_methodology import AnalysisMethodology


class ApplyMethodologyPromptBuilder:
    """방법론을 대상 종목 데이터에 대리 실행하는 프롬프트 빌더."""

    SYSTEM_INSTRUCTIONS = (
        "너는 딱주부TV 진행자의 분석 방법론을 대리 실행하는 애널리스트다. "
        "주어진 [방법론] 의 각 단계를 순서대로 [대상 종목 데이터] 에 적용하라. "
        "각 단계마다 사용한 데이터, 판단 내용, 강세/약세/중립 기여를 기록한다. "
        "방법론이 요구하는 데이터(예: 수급, 일봉 차트, 밴드)가 제공되지 않았으면 "
        "절대 추측하지 말고 missing_data 에 명시한 뒤 해당 단계의 assessment 를 "
        "'판단 보류' 로, view_contribution 을 '중립' 으로 처리한다. "
        "모든 단계를 종합해 overall_view (강세/약세/중립/관망) 와 confidence (0-100) 를 "
        "산출하되, 판단 보류 단계가 많을수록 confidence 를 낮춘다. "
        "caveats 에는 데이터 시점, 누락 데이터, 방법론 적용의 한계를 반드시 포함하고, "
        "summary 마지막에 이 분석이 투자 권유가 아닌 방법론 학습·시뮬레이션임을 명시한다. "
        "반드시 지정된 JSON 스키마로만 응답한다."
    )

    JSON_SCHEMA_GUIDE = """반드시 다음 JSON 형식으로만 응답하라. 다른 설명 텍스트·코드펜스 절대 금지.

{
  "methodology_name": "적용한 방법론 이름",
  "overall_view": "강세 | 약세 | 중립 | 관망 중 하나",
  "confidence": 0,
  "step_results": [
    {
      "step_order": 1,
      "step_name": "단계 이름",
      "data_used": "이 단계에서 실제 사용한 데이터 (없으면 '제공되지 않음')",
      "assessment": "판단 내용 (데이터 없으면 '판단 보류')",
      "view_contribution": "강세 | 약세 | 중립 중 하나"
    }
  ],
  "missing_data": ["방법론이 요구했으나 제공되지 않은 데이터"],
  "caveats": ["이 분석의 한계"],
  "summary": "종합 요약 (2~4문장, 마지막에 투자 권유가 아님을 명시)"
}
"""

    def build(
        self,
        methodology: AnalysisMethodology,
        stock_context: str,
        stock_name: str,
        ticker: str,
    ) -> str:
        method_lines = [f"방법론 이름: {methodology.methodology_name or '-'}"]
        for step in methodology.analysis_steps:
            method_lines.append(
                f"단계 {step.step_order}. {step.name}: {step.description}"
            )
            if step.indicators:
                method_lines.append(f"  - 필요 지표/데이터: {', '.join(step.indicators)}")
            for rule in step.decision_rules:
                method_lines.append(f"  - 판단 규칙: {rule}")
        if methodology.risk_management:
            method_lines.append(
                f"리스크 관리 원칙: {'; '.join(methodology.risk_management)}"
            )
        if methodology.applicable_market_conditions:
            method_lines.append(
                f"유효 시장 상황: {methodology.applicable_market_conditions}"
            )
        method_section = "\n".join(method_lines)

        return (
            f"[방법론]\n{method_section}\n\n"
            f"[대상 종목] {stock_name} ({ticker})\n\n"
            f"[대상 종목 데이터]\n{stock_context}\n\n"
            "위 방법론의 각 단계를 대상 종목 데이터에 순서대로 적용하고, "
            "지정된 JSON 스키마로만 결과를 반환하라.\n\n"
            f"{self.JSON_SCHEMA_GUIDE}"
        )
