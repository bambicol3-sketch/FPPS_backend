import json
import logging
from typing import Any, Optional

from app.domains.template_rag.application.port.llm_json_client_port import (
    LlmJsonClientPort,
)

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """당신은 raw data 를 보기 좋은 PPT 슬라이드로 시각화하는 디자이너입니다.
StyleGAN 처럼 **style_code(양식 디자인 코드)** 와 **content(raw data)** 가 분리되어 주어집니다.
당신은 모든 슬라이드에 style_code 를 일관되게 적용(AdaIN 처럼) 해야 합니다.

[입력]
- style_code : 양식에서 추출한 디자인 코드
  * color: { primary, secondary, accent, background, text_dark, text_light }
  * typography: { title, subtitle, body, caption } 각각 {size_pt, weight, color}
  * layout: { title_position, content_position, margin_pct, grid_columns }
  * decoration_style: { header_bar, header_bar_height_pct, header_bar_color, accent_line, bullet_marker, shape_corner }
  * mood / design_principles
- content : parsed raw 의 sections/key_values/bullets/numbers/metadata + 원문

[디자인 규칙 — style_code 를 절대적으로 따르라]
1. 색상은 오직 style_code.color 의 값만. 새 색 만들지 말 것.
2. 폰트 크기/색은 style_code.typography 의 title/subtitle/body/caption 매핑값 사용.
   - 슬라이드 제목 → title
   - 섹션 헤더 → subtitle
   - 본문/bullet → body
   - 보조 텍스트(날짜·페이지번호) → caption
3. layout.margin_pct 안쪽으로만 박스 배치. 박스 겹침 금지.
4. layout.title_position / content_position 패턴 따름.
5. decoration_style.header_bar=true 면 모든 본문 슬라이드에 헤더 바 추가 (color, height_pct 동일).
6. design_principles 의 원칙을 모든 슬라이드에 일관 적용.

[Content 시각화 규칙]
- 슬라이드 개수: raw 분량에 맞춰 4~10장
- 표지(1) → 요약(1) → 본문 섹션들 → 결론(0~1) 구성
- 핵심 수치는 큰 폰트 한 줄
- 항목은 style_code.decoration_style.bullet_marker 형식으로 (circle→"●", dash→"-", arrow→"➤")
- "라벨 : 값" 정렬, 비교 데이터는 표 형태로 줄별 정렬

[★최우선 규칙 — 환각 절대 금지★]
- 결과 box.text 의 모든 단어/수치/약어는 content(raw/parsed_raw) 에 명시되어야.
- 일반 비즈 프레임워크(SWOT, PEST, 4P, TAM/SAM/SOM, OKR 등) 도 content 에 없으면 금지.
- 의심스러우면 해당 박스를 만들지 말 것.

[피드백 반영]
이전 라운드 Discriminator 피드백이 주어지면 그 지적사항을 반드시 반영.

[응답 형식 — JSON 객체 1개]
{
  "slides": [
    {
      "title_hint": "표지",
      "boxes": [
        {
          "left_pct": 8, "top_pct": 38, "width_pct": 84, "height_pct": 14,
          "font_size_pt": 36, "bold": true, "color_hex": "FFFFFF",
          "align": "LEFT", "text": "보고서 제목"
        }
      ],
      "decorations": [
        { "type": "rect", "left_pct": 0, "top_pct": 0, "width_pct": 100,
          "height_pct": 6, "fill_color": "#1F3A5F" }
      ]
    }
  ]
}
"""


class GeneratorService:
    def __init__(self, llm: LlmJsonClientPort):
        self._llm = llm

    async def generate(
        self,
        style_code: dict[str, Any],
        parsed_raw: dict[str, Any],
        raw_text: str,
        style_strength: float = 1.0,
        previous: Optional[list[dict[str, Any]]] = None,
        feedback: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """style_code + content → 슬라이드 명세.

        style_strength: 0.0~1.0. 1.0 = style 완전 따름, 낮추면 generator 자유 ↑
        """
        style_txt = json.dumps(style_code, ensure_ascii=False, indent=2)[:5000]
        raw_struct_txt = (
            json.dumps(parsed_raw, ensure_ascii=False)[:7000] if parsed_raw else ""
        )
        raw_orig = raw_text[:5000] if not parsed_raw else ""

        prev_txt = ""
        if previous is not None:
            prev_txt = (
                f"\n[이전 라운드 결과]\n"
                f"{json.dumps(previous, ensure_ascii=False)[:5000]}\n"
            )
        fb_txt = ""
        if feedback:
            fb_txt = f"\n[Discriminator 피드백 — 반드시 반영]\n{feedback}\n"

        strength_hint = ""
        if style_strength >= 0.95:
            strength_hint = "style_code 를 매우 엄격히 따르세요 (모든 슬라이드 일관)."
        elif style_strength >= 0.7:
            strength_hint = "style_code 를 기본으로 따르되 일부 강조 표현 허용."
        else:
            strength_hint = "style_code 를 참고하되 가독성을 위해 일부 자율 조정 허용."

        user_prompt = (
            f"[style_code (양식 디자인 코드)]\n{style_txt}\n\n"
            f"[Style strength] {style_strength} — {strength_hint}\n\n"
            f"[content (raw)]\n"
            f"{('[parsed]\\n' + raw_struct_txt + chr(10)) if raw_struct_txt else ''}"
            f"{('[원문]\\n' + raw_orig) if raw_orig else ''}\n"
            f"{prev_txt}{fb_txt}\n"
            f"위 정보를 바탕으로 슬라이드를 설계하세요. style_code 모든 슬라이드 일관 적용. JSON 만."
        )

        try:
            result = await self._llm.generate_json(
                system_prompt=SYSTEM_PROMPT, user_prompt=user_prompt
            )
        except Exception as e:
            logger.exception("[Generator] LLM 호출 실패: %s", e)
            return previous or []

        slides = result.get("slides") or []
        normalized: list[dict[str, Any]] = []
        for i, s in enumerate(slides):
            boxes: list[dict] = []
            for b in (s.get("boxes") or []):
                text = (b.get("text") or "").strip()
                if not text:
                    continue
                boxes.append(
                    {
                        "left_pct": float(b.get("left_pct", 0) or 0),
                        "top_pct": float(b.get("top_pct", 0) or 0),
                        "width_pct": float(b.get("width_pct", 0) or 0),
                        "height_pct": float(b.get("height_pct", 0) or 0),
                        "font_size_pt": float(b.get("font_size_pt", 14) or 14),
                        "bold": bool(b.get("bold", False)),
                        "color_hex": (b.get("color_hex") or "").lstrip("#"),
                        "align": (b.get("align") or "LEFT").upper(),
                        "text": text,
                    }
                )
            decos: list[dict] = []
            for d in (s.get("decorations") or []):
                decos.append(
                    {
                        "type": (d.get("type") or "rect").lower(),
                        "left_pct": float(d.get("left_pct", 0) or 0),
                        "top_pct": float(d.get("top_pct", 0) or 0),
                        "width_pct": float(d.get("width_pct", 0) or 0),
                        "height_pct": float(d.get("height_pct", 0) or 0),
                        "fill_color": (d.get("fill_color") or d.get("color") or ""),
                        "color": (d.get("color") or d.get("fill_color") or ""),
                    }
                )
            if not boxes and not decos:
                continue
            normalized.append(
                {
                    "index": i,
                    "title_hint": s.get("title_hint", ""),
                    "boxes": boxes,
                    "decorations": decos,
                }
            )
        logger.info(
            "[Generator] 슬라이드 %d장 (style_strength=%s)",
            len(normalized), style_strength,
        )
        return normalized
