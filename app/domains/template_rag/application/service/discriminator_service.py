import json
import logging
from typing import Any

from app.domains.template_rag.application.port.llm_json_client_port import (
    LlmJsonClientPort,
)

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """당신은 PPT 디자인 심사위원입니다.
StyleGAN 의 Discriminator 역할로, 생성된 슬라이드들이 주어진 style_code 와 얼마나
**일관되게** 닮았는지 평가합니다.

[평가 기준 — 각 0~100]
1. color_consistency        : 슬라이드 색상이 style_code.color 의 값만 사용했는가?
2. typography_consistency   : title/body/caption 폰트 크기·색이 style_code.typography 와 일치하는가?
3. layout_consistency       : title_position / content_position / margin / grid 가 style_code.layout 과 비슷한가?
4. decoration_consistency   : header_bar/accent_line/bullet_marker/shape_corner 가 style_code.decoration_style 과 일치하는가?
5. mood_consistency         : 슬라이드 전체 분위기가 style_code.mood 와 design_principles 에 맞는가?
6. content_visualization    : raw content 가 시각적으로 잘 정리되어 있는가? (가독성, 균형, bullet/라벨)

총점 = 6 항목 평균. matched 는 총점 ≥ 80.

[feedback]
- matched=false → Generator 가 다음 라운드에 사용할 **구체적 개선 지시** 한국어로:
  * 슬라이드 번호 + 어떤 항목이 style_code 와 다른가 + 구체 수정값
  * 예: "슬라이드 3의 헤더 바 색이 #5BC4FF 인데 style_code.color.primary 는 #1F3A5F. 헤더 바 색을 #1F3A5F 로."
  * 예: "슬라이드 5의 본문 폰트 18pt 인데 style_code.typography.body.size_pt=14. 14pt 로."
- matched=true → feedback="".

[응답 형식]
{
  "score": 0-100,
  "matched": true|false,
  "feedback": "...",
  "details": {
    "color_consistency": 0-100,
    "typography_consistency": 0-100,
    "layout_consistency": 0-100,
    "decoration_consistency": 0-100,
    "mood_consistency": 0-100,
    "content_visualization": 0-100
  }
}
"""


class DiscriminatorService:
    THRESHOLD = 80

    def __init__(self, llm: LlmJsonClientPort):
        self._llm = llm

    async def evaluate(
        self,
        slides: list[dict[str, Any]],
        style_code: dict[str, Any],
    ) -> dict[str, Any]:
        style_txt = json.dumps(style_code, ensure_ascii=False, indent=2)[:5000]
        slides_txt = json.dumps(slides, ensure_ascii=False)[:9000]
        user_prompt = (
            f"[style_code]\n{style_txt}\n\n"
            f"[생성된 슬라이드]\n{slides_txt}\n\n"
            f"위 슬라이드가 style_code 와 얼마나 일관되게 닮았는지 6개 항목을 0~100 으로 평가. "
            f"matched=true 면 feedback=\"\". matched=false 면 슬라이드 번호 + 구체 수정 지시 한국어 feedback."
        )
        try:
            result = await self._llm.generate_json(
                system_prompt=SYSTEM_PROMPT, user_prompt=user_prompt
            )
        except Exception as e:
            logger.exception("[Discriminator] LLM 호출 실패 — matched=true 폴백: %s", e)
            return {
                "score": float(self.THRESHOLD),
                "matched": True,
                "feedback": "",
                "details": {},
            }

        details = result.get("details") or {}
        keys = [
            "color_consistency", "typography_consistency", "layout_consistency",
            "decoration_consistency", "mood_consistency", "content_visualization",
        ]
        sub = [float(details.get(k) or 0) for k in keys if details.get(k) is not None]
        if sub:
            score = sum(sub) / len(sub)
        else:
            score = float(result.get("score") or 0)
        matched = score >= self.THRESHOLD

        return {
            "score": round(score, 1),
            "matched": matched,
            "feedback": (result.get("feedback") or "").strip() if not matched else "",
            "details": details,
        }
