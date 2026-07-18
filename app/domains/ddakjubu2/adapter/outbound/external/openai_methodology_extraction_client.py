import json
from datetime import datetime, timezone
from typing import Any, Dict

from openai import AsyncOpenAI

from app.domains.ddakjubu2.application.port.methodology_extraction_port import (
    MethodologyExtractionPort,
)
from app.domains.ddakjubu2.domain.entity.analysis_methodology import AnalysisMethodology
from app.domains.ddakjubu2.domain.entity.learning_note import LearningNote
from app.domains.ddakjubu2.domain.entity.source_video import SourceVideo
from app.domains.ddakjubu2.domain.service.methodology_prompt_builder import (
    MethodologyPromptBuilder,
)
from app.domains.ddakjubu2.infrastructure.mapper.methodology_mapper import (
    MethodologyMapper,
)


def parse_llm_json(raw_text: str, fallback: Dict[str, Any]) -> Dict[str, Any]:
    """코드펜스 제거 후 JSON 파싱. 실패 시 fallback 반환."""
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
    print("[ddakjubu2_methodology] LLM 응답 JSON 파싱 실패, 빈 결과 반환")
    return fallback


class OpenAIMethodologyExtractionClient(MethodologyExtractionPort):
    """OpenAI Responses API 로 영상의 분석 방법론을 추출하는 3차 패스 어댑터."""

    def __init__(self, api_key: str, model: str = "gpt-5-mini"):
        self._client = AsyncOpenAI(api_key=api_key)
        self._model = model
        self._prompt_builder = MethodologyPromptBuilder()

    async def extract(
        self, source_video: SourceVideo, note: LearningNote
    ) -> AnalysisMethodology:
        prompt = self._prompt_builder.build(source_video, note)

        try:
            response = await self._client.responses.create(
                model=self._model,
                input=[
                    {
                        "role": "system",
                        "content": MethodologyPromptBuilder.SYSTEM_INSTRUCTIONS,
                    },
                    {"role": "user", "content": prompt},
                ],
                reasoning={"effort": "minimal"},
            )
            raw_text = response.output_text or ""
        except Exception as e:
            print(
                f"[ddakjubu2_methodology] OpenAI 호출 실패 "
                f"video_id={source_video.video_id} error={e}"
            )
            raise

        parsed = parse_llm_json(raw_text, fallback={"analysis_steps": []})

        return MethodologyMapper.from_json(
            parsed,
            video_id=source_video.video_id,
            video_title=source_video.title,
            extracted_at=datetime.now(timezone.utc),
        )
