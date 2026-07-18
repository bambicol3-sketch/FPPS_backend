from datetime import datetime, timezone

from openai import AsyncOpenAI

from app.domains.ddakjubu2.adapter.outbound.external.openai_methodology_extraction_client import (
    parse_llm_json,
)
from app.domains.ddakjubu2.application.port.methodology_apply_port import (
    MethodologyApplyPort,
)
from app.domains.ddakjubu2.domain.entity.analysis_methodology import AnalysisMethodology
from app.domains.ddakjubu2.domain.entity.applied_analysis import AppliedAnalysis
from app.domains.ddakjubu2.domain.service.apply_methodology_prompt_builder import (
    ApplyMethodologyPromptBuilder,
)
from app.domains.ddakjubu2.infrastructure.mapper.applied_analysis_mapper import (
    AppliedAnalysisMapper,
)

VALID_VIEWS = {"강세", "약세", "중립", "관망"}


class OpenAIMethodologyApplyClient(MethodologyApplyPort):
    """방법론을 대상 종목 데이터에 대리 실행하는 OpenAI 어댑터."""

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-5-mini",
        reasoning_effort: str = "low",
    ):
        self._client = AsyncOpenAI(api_key=api_key)
        self._model = model
        self._reasoning_effort = reasoning_effort
        self._prompt_builder = ApplyMethodologyPromptBuilder()

    async def apply(
        self,
        methodology: AnalysisMethodology,
        stock_context: str,
        stock_name: str,
        ticker: str,
    ) -> AppliedAnalysis:
        prompt = self._prompt_builder.build(
            methodology, stock_context, stock_name, ticker
        )

        try:
            response = await self._client.responses.create(
                model=self._model,
                input=[
                    {
                        "role": "system",
                        "content": ApplyMethodologyPromptBuilder.SYSTEM_INSTRUCTIONS,
                    },
                    {"role": "user", "content": prompt},
                ],
                reasoning={"effort": self._reasoning_effort},
            )
            raw_text = response.output_text or ""
        except Exception as e:
            print(
                f"[ddakjubu2_apply] OpenAI 호출 실패 ticker={ticker} error={e}"
            )
            raise

        parsed = parse_llm_json(raw_text, fallback={})

        overall_view = str(parsed.get("overall_view", "")).strip()
        if overall_view not in VALID_VIEWS:
            overall_view = "관망"
        try:
            confidence = max(0, min(100, int(parsed.get("confidence", 0))))
        except (TypeError, ValueError):
            confidence = 0

        parsed.setdefault("methodology_name", methodology.methodology_name)
        parsed["analyzed_at"] = datetime.now(timezone.utc).isoformat()

        analysis = AppliedAnalysisMapper.from_json(
            parsed,
            ticker=ticker,
            stock_name=stock_name,
            mode="",  # usecase 에서 채운다
            video_id=None,
            overall_view=overall_view,
            confidence=confidence,
        )
        return analysis
