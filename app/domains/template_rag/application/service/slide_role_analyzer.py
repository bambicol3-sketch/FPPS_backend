import logging
from typing import Any

from app.domains.template_rag.application.port.llm_json_client_port import (
    LlmJsonClientPort,
)

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """당신은 PPT 양식을 분석하는 전문가입니다.
주어진 PPT 양식의 각 슬라이드 텍스트를 분석해서 슬라이드별 역할과 슬롯 의미를 추출합니다.

규칙:
- 각 슬라이드의 role 은 다음 중 하나: "cover" | "toc" | "section_header" | "body" | "data" | "conclusion" | "blank" | "other"
- topic 은 한 줄로 슬라이드 주제를 요약 (예: "Q4 매출 현황 요약", "리스크 항목 나열")
- slot_description: 이 슬라이드 본문 슬롯에 어떤 내용이 들어가야 하는지 (예: "월별 매출 추이 데이터", "주요 이슈 3~5개 bullet")
- body_max_chars: 본문 슬롯에 들어갈 적절한 최대 글자 수 (도형 크기 고려해서 80~600 사이)
- 슬라이드 텍스트가 없거나 의미를 모르겠으면 role="blank", body_max_chars=200

응답은 반드시 다음 JSON 형식의 객체:
{
  "slides": [
    {
      "index": 0,
      "role": "cover",
      "topic": "표지",
      "slot_description": "보고서 제목과 작성일",
      "body_max_chars": 80
    },
    ...
  ]
}
"""


class SlideRoleAnalyzer:
    def __init__(self, llm: LlmJsonClientPort):
        self._llm = llm

    async def analyze(self, slide_texts: list[str]) -> list[dict[str, Any]]:
        """양식 슬라이드 텍스트 리스트 → 각 슬라이드 role 정보 dict 리스트."""
        slides_input = "\n\n".join(
            f"[슬라이드 {i}]\n{text or '(텍스트 없음)'}"
            for i, text in enumerate(slide_texts)
        )

        user_prompt = (
            f"다음 PPT 양식 슬라이드 {len(slide_texts)}장을 분석하세요. "
            f"각 슬라이드의 텍스트는 아래와 같습니다:\n\n{slides_input}"
        )

        try:
            result = await self._llm.generate_json(
                system_prompt=SYSTEM_PROMPT,
                user_prompt=user_prompt,
            )
        except Exception as e:
            logger.exception("[SlideRoleAnalyzer] LLM 호출 실패: %s", e)
            result = {}

        raw_slides = result.get("slides") or []
        # 모자라면 기본값으로 채움
        normalized: list[dict[str, Any]] = []
        for i in range(len(slide_texts)):
            match = next(
                (s for s in raw_slides if int(s.get("index", -1)) == i), None
            )
            if match is None:
                normalized.append(
                    {
                        "index": i,
                        "role": "blank" if not slide_texts[i].strip() else "other",
                        "topic": "",
                        "slot_description": "",
                        "body_max_chars": 200,
                    }
                )
            else:
                normalized.append(
                    {
                        "index": i,
                        "role": match.get("role", "other"),
                        "topic": match.get("topic", ""),
                        "slot_description": match.get("slot_description", ""),
                        "body_max_chars": int(match.get("body_max_chars", 200) or 200),
                    }
                )
        logger.info(
            "[SlideRoleAnalyzer] 양식 슬라이드 %d장 분석 완료", len(normalized)
        )
        return normalized
