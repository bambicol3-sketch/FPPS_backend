import logging
from typing import Any

from app.domains.template_rag.application.port.llm_json_client_port import (
    LlmJsonClientPort,
)

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """당신은 비정형 raw data (보고서/문서/메모) 를 분석해 구조화된 데이터로 변환하는 전문가입니다.

[해야 할 일]
주어진 raw 텍스트를 읽고 다음 정보를 JSON 으로 추출합니다.
- summary: 전체 raw 의 1-2 문장 요약
- sections: 의미 단위 섹션들 [{heading, content, key_values{}, bullets[]}]
- key_values: 전체에서 추출한 라벨-값 쌍 (예: {"매출": "12.3억", "기간": "Q4 2025"})
- bullets: 핵심 포인트/항목들 (한 줄씩, 최대 12개)
- numbers: 수치 데이터 [{label, value, unit?}]
- metadata: {date?, author?, doc_type?, keywords[]}

규칙:
- raw 에 명시된 사실/수치만 사용. 추측·창작 금지.
- 표/리스트는 가능한 한 sections.bullets 또는 numbers 로 정형화.
- 한국어로 작성. raw 가 영어면 자연스러운 한국어로.

[응답 형식 — JSON 객체 1개]
{
  "summary": "...",
  "sections": [
    {
      "heading": "매출 개요",
      "content": "Q4 매출 12.3억 ...",
      "key_values": {"매출": "12.3억", "전분기 대비": "+8%"},
      "bullets": ["신제품 A 출시", "B 사업부 흑자 전환"]
    }
  ],
  "key_values": {"기간": "Q4 2025", "총매출": "12.3억"},
  "bullets": ["...", "..."],
  "numbers": [{"label": "매출", "value": 12.3, "unit": "억원"}],
  "metadata": {"date": "2025-12-31", "doc_type": "분기 보고서", "keywords": ["매출", "신제품"]}
}
"""


class RawDataParser:
    def __init__(self, llm: LlmJsonClientPort):
        self._llm = llm

    async def parse(self, raw_text: str) -> dict[str, Any]:
        max_chars = 16000
        if len(raw_text) > max_chars:
            raw_text = raw_text[:max_chars] + "\n...(이하 생략)"

        user_prompt = (
            f"[raw data]\n{raw_text}\n\n"
            f"위 raw 텍스트를 분석해 summary/sections/key_values/bullets/numbers/metadata 를 JSON 으로 출력하세요."
        )
        try:
            result = await self._llm.generate_json(
                system_prompt=SYSTEM_PROMPT, user_prompt=user_prompt
            )
        except Exception as e:
            logger.exception("[RawDataParser] LLM 호출 실패: %s", e)
            result = {}

        out = {
            "summary": result.get("summary") or "",
            "sections": result.get("sections") or [],
            "key_values": result.get("key_values") or {},
            "bullets": result.get("bullets") or [],
            "numbers": result.get("numbers") or [],
            "metadata": result.get("metadata") or {},
        }
        logger.info(
            "[RawDataParser] 파싱 완료: sections=%d, kv=%d, bullets=%d, numbers=%d",
            len(out["sections"]), len(out["key_values"]),
            len(out["bullets"]), len(out["numbers"]),
        )
        return out
