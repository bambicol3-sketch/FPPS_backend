import json
import logging

from openai import AsyncOpenAI

from app.domains.pdf_to_ppt.application.port.slide_outline_generator_port import (
    SlideOutlineGeneratorPort,
)
from app.domains.pdf_to_ppt.domain.value_object.slide_outline import SlideOutline
from app.infrastructure.config.settings import get_settings

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
    "당신은 문서를 발표용 슬라이드 구조로 요약하는 전문가입니다. "
    "주어진 문서 텍스트를 읽고 핵심 내용을 슬라이드 단위로 나눠, "
    "각 슬라이드마다 제목 하나와 3~5개의 핵심 불릿 포인트를 작성하세요. "
    "불릿은 원문을 그대로 복사하지 말고 핵심만 간결한 한 문장으로 요약하세요."
)


class OpenAiOutlineGeneratorImpl(SlideOutlineGeneratorPort):
    def __init__(self) -> None:
        settings = get_settings()
        self._client = AsyncOpenAI(api_key=settings.openai_api_key)
        self._model = settings.openai_finance_agent_model

    async def generate(self, text: str, max_slides: int) -> list[SlideOutline]:
        prompt = (
            f"{_SYSTEM_PROMPT}\n\n"
            f"최대 슬라이드 수: {max_slides}\n\n"
            f"[문서 텍스트]\n{text}\n\n"
            f"[출력 형식] 다음 JSON 객체 하나만 반환 (마크다운/설명 없이 JSON 그 자체만):\n"
            f'{{"slides": [{{"title": "...", "bullets": ["...", "..."]}}]}}'
        )
        try:
            response = await self._client.responses.create(
                model=self._model,
                input=prompt,
                text={"format": {"type": "json_object"}},
            )
        except TypeError:
            response = await self._client.responses.create(
                model=self._model,
                input=prompt,
            )

        raw = (response.output_text or "").strip()
        if raw.startswith("```"):
            raw = raw.strip("`")
            if raw.lower().startswith("json"):
                raw = raw[4:]
            raw = raw.strip()

        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as e:
            logger.warning(
                "[OpenAiOutlineGenerator] JSON 파싱 실패: %s | raw=%s", e, raw[:500]
            )
            return []

        slides_raw = parsed.get("slides", []) if isinstance(parsed, dict) else []
        outline: list[SlideOutline] = []
        for item in slides_raw:
            if not isinstance(item, dict):
                continue
            title = str(item.get("title") or "").strip()
            bullets = [
                str(b).strip() for b in (item.get("bullets") or []) if str(b).strip()
            ]
            if title:
                outline.append(SlideOutline(title=title, bullets=bullets))
        return outline[:max_slides]
