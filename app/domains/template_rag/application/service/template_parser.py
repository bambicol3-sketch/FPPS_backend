import logging
from typing import Any

from app.domains.template_rag.application.port.llm_json_client_port import (
    LlmJsonClientPort,
)

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """당신은 PPT 양식(.pptx)을 분석해 구조화된 명세서로 변환하는 전문가입니다.
주어진 양식의 슬라이드별 박스/도형 메타데이터와 원본 텍스트를 보고 각 슬라이드의
의도/역할/슬롯 의미/디자인 톤을 추출해 JSON 으로 답변합니다.

[해야 할 일]
- 각 슬라이드의 role 분류:
  "cover" | "toc" | "section_header" | "agenda" | "body" | "data" | "comparison" |
  "timeline" | "image_focus" | "conclusion" | "blank" | "other"
- 각 슬라이드의 topic: 한 줄로 슬라이드 주제 요약
- 각 텍스트 박스의 slot_name: "title" | "subtitle" | "body" | "bullets" | "metric" |
  "label" | "caption" | "footer" | "date" | "page_number" | "other"
- 각 텍스트 박스의 purpose: 어떤 raw 내용이 들어가야 적합한지 짧게 설명
- 슬라이드의 style_notes: 디자인 톤 한 줄 (예: "헤더 바 + 좌측 정렬 본문, 네이비 강조")
- design_pattern: 슬라이드의 시각적 패턴 (예: "header_bar" | "split_two_column" | "centered_title" | "grid" | "bullet_list" 등)

[응답 형식 — JSON 객체 1개]
{
  "color_palette_inferred": ["#1F3A5F", ...],
  "slides": [
    {
      "index": 0,
      "role": "cover",
      "topic": "표지",
      "design_pattern": "centered_title",
      "style_notes": "중앙 정렬, 네이비 헤더 바",
      "slots": [
        {"box_id": 0, "slot_name": "title", "purpose": "보고서 제목"},
        {"box_id": 1, "slot_name": "subtitle", "purpose": "보고 기간 또는 작성일"}
      ]
    },
    ...
  ]
}
"""


class TemplateParser:
    def __init__(self, llm: LlmJsonClientPort):
        self._llm = llm

    @staticmethod
    def _summarize_template_for_llm(
        slides_boxes: list[list[dict]],
        slides_shapes: list[list[dict]],
    ) -> str:
        lines: list[str] = []
        for i in range(max(len(slides_boxes), len(slides_shapes))):
            lines.append(f"슬라이드 {i}:")
            boxes = slides_boxes[i] if i < len(slides_boxes) else []
            shapes = slides_shapes[i] if i < len(slides_shapes) else []
            for b in boxes:
                font = b.get("font_size_pt") or 14
                bold = "bold" if b.get("bold") else "regular"
                color = b.get("color_hex") or "default"
                orig = b.get("original_text", "")
                orig_short = orig[:80] + ("…" if len(orig) > 80 else "")
                lines.append(
                    f"  텍스트박스{b['box_id']}: pos({b['left_pct']}%,{b['top_pct']}%) "
                    f"size({b['width_pct']}%×{b['height_pct']}%) font {font}pt {bold} {color} "
                    f"원본='{orig_short}'"
                )
            for j, s in enumerate(shapes):
                lines.append(
                    f"  도형{j}: type={s.get('shape_type')} "
                    f"pos({s['left_pct']}%,{s['top_pct']}%) "
                    f"size({s['width_pct']}%×{s['height_pct']}%) fill={s.get('fill_color') or '-'}"
                )
            lines.append("")
        return "\n".join(lines)

    async def parse(
        self,
        slides_boxes: list[list[dict]],
        slides_shapes: list[list[dict]],
        color_palette: list[str],
    ) -> dict[str, Any]:
        """양식 메타데이터 → 슬라이드별 구조 파싱 결과."""
        summary = self._summarize_template_for_llm(slides_boxes, slides_shapes)
        palette_str = ", ".join(color_palette) if color_palette else "(없음)"
        user_prompt = (
            f"[양식 색상 팔레트 (자동 추출)] {palette_str}\n\n"
            f"[양식 슬라이드 메타데이터]\n{summary}\n\n"
            f"위 양식의 각 슬라이드를 분석해 role/topic/design_pattern/style_notes/slots 를 JSON 으로 출력하세요."
        )
        try:
            result = await self._llm.generate_json(
                system_prompt=SYSTEM_PROMPT, user_prompt=user_prompt
            )
        except Exception as e:
            logger.exception("[TemplateParser] LLM 호출 실패: %s", e)
            result = {}

        slides_out = result.get("slides") or []
        normalized: list[dict[str, Any]] = []
        for i in range(len(slides_boxes)):
            match = next(
                (s for s in slides_out if int(s.get("index", -1)) == i), None
            )
            if match is None:
                # 빈 슬라이드는 blank 로
                empty = not (slides_boxes[i] or (slides_shapes[i] if i < len(slides_shapes) else []))
                normalized.append(
                    {
                        "index": i,
                        "role": "blank" if empty else "other",
                        "topic": "",
                        "design_pattern": "",
                        "style_notes": "",
                        "slots": [],
                    }
                )
            else:
                normalized.append(
                    {
                        "index": i,
                        "role": match.get("role", "other"),
                        "topic": match.get("topic", ""),
                        "design_pattern": match.get("design_pattern", ""),
                        "style_notes": match.get("style_notes", ""),
                        "slots": match.get("slots") or [],
                    }
                )
        out = {
            "color_palette_inferred": result.get("color_palette_inferred") or [],
            "slides": normalized,
        }
        logger.info("[TemplateParser] 양식 %d장 파싱 완료", len(normalized))
        return out
