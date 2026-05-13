import json
import logging
from typing import Any

from app.domains.template_rag.application.port.llm_json_client_port import (
    LlmJsonClientPort,
)

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """당신은 PPT 양식의 디자인 스타일을 추출해 정형화된 style_code 로 만드는 디자이너입니다.
주어진 양식 슬라이드 메타데이터(텍스트 박스 위치/크기/폰트/색상, 비텍스트 도형, 색상 통계)를 분석해서
**양식 전체에 걸친 일관된 디자인 코드** 를 추출합니다.

style_code 의 역할: 이후 Generator 가 raw data 로 새 슬라이드를 만들 때 이 style 을
모든 슬라이드에 일관되게 적용 (StyleGAN 의 AdaIN 처럼).

[추출 항목 — 모두 양식에서 관찰된 값으로]
1. color
   - primary    : 가장 두드러진 강조 색 (헤더 바 등)
   - secondary  : 보조 색
   - accent     : 강조/포인트 색
   - background : 슬라이드 주 배경 색 (대부분 흰색 또는 양식 어두운 배경)
   - text_dark  : 어두운 배경 위에서 사용되는 텍스트 색 (대개 흰색 계열)
   - text_light : 밝은 배경 위에서 사용되는 텍스트 색 (대개 어두운 회색/검정)

2. typography
   - title    : {size_pt, weight, color}  슬라이드 제목용
   - subtitle : {size_pt, weight, color}  부제목/섹션
   - body     : {size_pt, weight, color}  본문
   - caption  : {size_pt, weight, color}  보조 텍스트

3. layout
   - title_position  : "top_left" | "top_center" | "center" | "top_right" 중 양식이 자주 쓰는 패턴
   - content_position: "below_title" | "left" | "right" | "split_two_column" | "centered"
   - margin_pct      : { top, right, bottom, left }  슬라이드 안전 마진 %
   - grid_columns    : 1 | 2 | 3 (대부분 본문이 몇 컬럼인지)

4. decoration_style
   - header_bar           : true/false (양식이 헤더 바를 자주 사용하는지)
   - header_bar_height_pct: 사용 시 % 높이
   - header_bar_color     : color.primary 또는 양식 색
   - accent_line          : true/false
   - bullet_marker        : "circle" | "square" | "dash" | "arrow" | "none"
   - shape_corner         : "sharp" | "rounded"

5. mood : "corporate_minimal" | "data_dense" | "playful" | "editorial" | "techy" | "soft_pastel" 등 한 단어

6. design_principles : 양식의 디자인 원칙을 짧은 문장 3~5개 (한국어)
   예: "어두운 헤더 바 위에 흰색 제목", "본문은 좌측 정렬 + bullet", "강조 색은 시안 계열"

[★규칙★]
- 모든 색상은 양식에서 관찰된 색만. 새 색 만들지 말 것.
- 폰트 크기는 양식의 typical 값 사용.
- 모르겠거나 양식에 없는 항목은 적절한 기본값 (예: bullet_marker "circle", shape_corner "sharp", margin 5%)

[응답 형식 — JSON 객체 1개]
{
  "color": { "primary":"#1F3A5F", "secondary":"#163E75", "accent":"#5BC4FF",
             "background":"#FFFFFF", "text_dark":"#FFFFFF", "text_light":"#1F3A5F" },
  "typography": {
    "title":   {"size_pt":36,"weight":"bold","color":"#FFFFFF"},
    "subtitle":{"size_pt":20,"weight":"regular","color":"#FFFFFF"},
    "body":    {"size_pt":14,"weight":"regular","color":"#1F3A5F"},
    "caption": {"size_pt":10,"weight":"regular","color":"#888888"}
  },
  "layout": {
    "title_position":"top_left","content_position":"below_title",
    "margin_pct":{"top":5,"right":8,"bottom":5,"left":8},"grid_columns":1
  },
  "decoration_style": {
    "header_bar":true,"header_bar_height_pct":6,"header_bar_color":"#1F3A5F",
    "accent_line":true,"bullet_marker":"circle","shape_corner":"sharp"
  },
  "mood":"corporate_minimal",
  "design_principles":[
    "어두운 헤더 바 위에 흰색 제목",
    "본문은 좌측 정렬 + 원형 bullet",
    "강조 색은 시안 계열 액센트로 사용"
  ]
}
"""


class StyleExtractor:
    def __init__(self, llm: LlmJsonClientPort):
        self._llm = llm

    @staticmethod
    def _summarize_template_for_style(
        slides_boxes: list[list[dict]],
        slides_shapes: list[list[dict]],
        color_palette: list[str],
        font_palette: list[str],
        font_size_palette: list[float],
    ) -> str:
        lines: list[str] = []
        lines.append(f"[색상 통계] 자주 쓰이는 fill: {', '.join(color_palette) or '-'}")
        lines.append(f"[폰트 색상 통계] {', '.join(font_palette) or '-'}")
        lines.append(
            f"[폰트 크기 통계] {', '.join(str(s) + 'pt' for s in font_size_palette) or '-'}"
        )
        lines.append("")
        # 슬라이드 샘플 (앞 8장만)
        for i in range(min(8, max(len(slides_boxes), len(slides_shapes)))):
            lines.append(f"슬라이드 {i}:")
            for b in (slides_boxes[i] if i < len(slides_boxes) else []):
                lines.append(
                    f"  텍스트박스: pos({b.get('left_pct')}%,{b.get('top_pct')}%) "
                    f"size({b.get('width_pct')}%×{b.get('height_pct')}%) "
                    f"font {b.get('font_size_pt') or '?'}pt {('bold' if b.get('bold') else '-')} "
                    f"color={b.get('color_hex') or '-'} align={b.get('align') or '-'}"
                )
            for s in (slides_shapes[i] if i < len(slides_shapes) else []):
                lines.append(
                    f"  도형: type={s.get('shape_type')} "
                    f"pos({s.get('left_pct')}%,{s.get('top_pct')}%) "
                    f"size({s.get('width_pct')}%×{s.get('height_pct')}%) "
                    f"fill={s.get('fill_color') or '-'}"
                )
            lines.append("")
        return "\n".join(lines)

    async def extract(
        self,
        slides_boxes: list[list[dict]],
        slides_shapes: list[list[dict]],
        color_palette: list[str],
        font_palette: list[str],
        font_size_palette: list[float],
    ) -> dict[str, Any]:
        summary = self._summarize_template_for_style(
            slides_boxes, slides_shapes, color_palette, font_palette, font_size_palette
        )
        user_prompt = (
            f"[양식 메타데이터 요약]\n{summary}\n\n"
            f"위 양식을 분석해 style_code JSON 을 추출하세요."
        )
        try:
            result = await self._llm.generate_json(
                system_prompt=SYSTEM_PROMPT, user_prompt=user_prompt
            )
        except Exception as e:
            logger.exception("[StyleExtractor] LLM 호출 실패 — fallback style 사용: %s", e)
            return self._fallback(color_palette, font_palette, font_size_palette)

        # 기본값 보강
        style = self._fallback(color_palette, font_palette, font_size_palette)
        if result:
            self._merge(style, result)
        logger.info(
            "[StyleExtractor] style_code 추출 완료: mood=%s primary=%s",
            style.get("mood"), style.get("color", {}).get("primary"),
        )
        return style

    @staticmethod
    def _fallback(
        color_palette: list[str],
        font_palette: list[str],
        font_size_palette: list[float],
    ) -> dict[str, Any]:
        primary = color_palette[0] if color_palette else "#1F3A5F"
        secondary = color_palette[1] if len(color_palette) > 1 else primary
        accent = color_palette[2] if len(color_palette) > 2 else secondary
        text_dark_bg = "#FFFFFF"
        text_light_bg = font_palette[0] if font_palette else "#1F3A5F"
        sizes_sorted = sorted(font_size_palette or [36.0, 20.0, 14.0, 10.0], reverse=True)
        while len(sizes_sorted) < 4:
            sizes_sorted.append(sizes_sorted[-1] * 0.6)
        return {
            "color": {
                "primary": _norm_hex(primary),
                "secondary": _norm_hex(secondary),
                "accent": _norm_hex(accent),
                "background": "#FFFFFF",
                "text_dark": _norm_hex(text_dark_bg),
                "text_light": _norm_hex(text_light_bg),
            },
            "typography": {
                "title":    {"size_pt": float(sizes_sorted[0]), "weight": "bold",    "color": _norm_hex(text_dark_bg)},
                "subtitle": {"size_pt": float(sizes_sorted[1]), "weight": "regular", "color": _norm_hex(text_dark_bg)},
                "body":     {"size_pt": float(sizes_sorted[2]), "weight": "regular", "color": _norm_hex(text_light_bg)},
                "caption":  {"size_pt": float(sizes_sorted[3]), "weight": "regular", "color": "#888888"},
            },
            "layout": {
                "title_position": "top_left",
                "content_position": "below_title",
                "margin_pct": {"top": 5, "right": 8, "bottom": 5, "left": 8},
                "grid_columns": 1,
            },
            "decoration_style": {
                "header_bar": True,
                "header_bar_height_pct": 6,
                "header_bar_color": _norm_hex(primary),
                "accent_line": True,
                "bullet_marker": "circle",
                "shape_corner": "sharp",
            },
            "mood": "corporate_minimal",
            "design_principles": [
                "양식 색상 팔레트 내에서만 색상 사용",
                "제목은 상단, 본문은 그 아래",
                "장식은 헤더 바와 액센트 라인 정도로 절제",
            ],
        }

    @staticmethod
    def _merge(base: dict, overrides: dict) -> None:
        for k, v in overrides.items():
            if (
                isinstance(v, dict)
                and isinstance(base.get(k), dict)
            ):
                StyleExtractor._merge(base[k], v)
            elif v is not None and v != "":
                base[k] = v


def _norm_hex(value: str | None) -> str:
    if not value:
        return "#000000"
    v = str(value).strip()
    if not v.startswith("#"):
        v = "#" + v
    return v.upper()
