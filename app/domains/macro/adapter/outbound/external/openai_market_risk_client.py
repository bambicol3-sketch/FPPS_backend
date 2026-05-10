import json
import logging
from typing import Any, Dict, List

from openai import AsyncOpenAI

from app.domains.macro.application.port.market_risk_llm_port import (
    LlmRiskResult,
    MarketRiskLlmPort,
)

logger = logging.getLogger(__name__)


class OpenAIMarketRiskClient(MarketRiskLlmPort):
    """OpenAI Responses API (gpt-5-mini)를 사용해 시장 Risk-on/Risk-off를 판단한다."""

    def __init__(self, api_key: str, model: str = "gpt-5-mini"):
        self._client = AsyncOpenAI(api_key=api_key)
        self._model = model

    async def ask(self, system_instructions: str, user_prompt: str) -> LlmRiskResult:
        response = await self._client.responses.create(
            model=self._model,
            input=[
                {"role": "system", "content": system_instructions},
                {"role": "user", "content": user_prompt},
            ],
            reasoning={"effort": "minimal"},
        )
        raw_text = response.output_text or ""

        parsed = self._parse_json(raw_text)
        stance = str(parsed.get("stance", "")).strip() or "Unknown"
        reasons = [str(r).strip() for r in (parsed.get("reasons") or []) if r]

        return LlmRiskResult(stance=stance, reasons=reasons, raw_text=raw_text)

    @staticmethod
    def _parse_json(raw_text: str) -> Dict[str, Any]:
        text = raw_text.strip()
        if text.startswith("```"):
            text = text.strip("`")
            if text.lower().startswith("json"):
                text = text[4:]
            text = text.strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            start = text.find("{")
            end = text.rfind("}")
            if start != -1 and end != -1 and end > start:
                try:
                    return json.loads(text[start:end + 1])
                except json.JSONDecodeError:
                    pass
        logger.warning("[macro_llm] 응답 JSON 파싱 실패, 빈 결과 반환")
        return {"stance": "Unknown", "reasons": []}
