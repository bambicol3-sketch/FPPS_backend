from datetime import datetime, timezone
from typing import List

from openai import AsyncOpenAI

from app.domains.ddakjubu2.adapter.outbound.external.openai_methodology_extraction_client import (
    parse_llm_json,
)
from app.domains.ddakjubu2.application.port.methodology_merge_port import (
    MethodologyMergePort,
)
from app.domains.ddakjubu2.domain.entity.analysis_methodology import AnalysisMethodology
from app.domains.ddakjubu2.domain.service.methodology_merge_prompt_builder import (
    MethodologyMergePromptBuilder,
)
from app.domains.ddakjubu2.infrastructure.mapper.methodology_mapper import (
    MethodologyMapper,
)


class OpenAIMethodologyMergeClient(MethodologyMergePort):
    """여러 방법론을 마스터 프로파일로 통합하는 OpenAI 어댑터."""

    def __init__(self, api_key: str, model: str = "gpt-5-mini"):
        self._client = AsyncOpenAI(api_key=api_key)
        self._model = model
        self._prompt_builder = MethodologyMergePromptBuilder()

    async def merge(
        self, methodologies: List[AnalysisMethodology]
    ) -> AnalysisMethodology:
        prompt = self._prompt_builder.build(methodologies)

        try:
            response = await self._client.responses.create(
                model=self._model,
                input=[
                    {
                        "role": "system",
                        "content": MethodologyMergePromptBuilder.SYSTEM_INSTRUCTIONS,
                    },
                    {"role": "user", "content": prompt},
                ],
                reasoning={"effort": "low"},
            )
            raw_text = response.output_text or ""
        except Exception as e:
            print(f"[ddakjubu2_methodology] 마스터 병합 OpenAI 호출 실패 error={e}")
            raise

        parsed = parse_llm_json(raw_text, fallback={"analysis_steps": []})

        return MethodologyMapper.from_json(
            parsed,
            video_id="",
            video_title="딱주부 종합 방법론",
            extracted_at=datetime.now(timezone.utc),
        )
