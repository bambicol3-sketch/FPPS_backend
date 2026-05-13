import json
import logging
from typing import Any

from app.domains.template_rag.application.port.llm_json_client_port import (
    LlmJsonClientPort,
)

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """당신은 PPT 슬라이드 디자인 검토 전문가입니다.

이미 raw data 매핑이 끝난 슬라이드들의 boxes(텍스트 박스) 와 decorations(장식 도형) 가 주어집니다.
이를 보고 **시각적 가독성, 균형, 양식 디자인 일관성** 측면에서 다음을 개선/다듬어 주세요.

[개선 가능 항목]
1. 박스 텍스트 분량 조정 — 박스 크기(width × height × font_size 로 추정)를 넘치는 텍스트는 핵심만 남기고 줄임.
2. 박스 텍스트 포맷팅 — 단순 텍스트 나열이면 bullet(•) / 번호(1. 2. 3.) / "라벨 : 값" 정렬로 시각적 정리.
3. decoration 추가/조정 — 슬라이드가 너무 비어 보이면 양식 팔레트 색상으로 헤더 바, 액센트 라인, 마커 추가.
4. use 재검토 — boxes 의 합계 글자가 매우 빈약(≤ 20자)하거나 의미가 거의 없으면 use=false.
5. 슬라이드 간 일관성 — 같은 슬라이드 내 폰트 스타일이 어울리는지, decoration 색상이 양식과 어울리는지.

[★최우선 규칙★]
- raw_text/parsed_raw 에 없는 단어·수치·고유명사·약어를 새로 만들지 말 것. 기존 텍스트의 분량/형식만 다듬을 수 있음.
- box.box_id 는 반드시 보존. 새 box 추가 금지.
- decoration 색상은 반드시 color_palette 내에서만.
- 박스 안 텍스트가 이미 비어 있으면 그대로 둘 것.

[응답 형식 — 매퍼와 동일]
{
  "slides": [
    {
      "index": 0,
      "use": true,
      "boxes": [ { "box_id": 0, "text": "..." }, ... ],
      "decorations": [
        { "type": "rect", "left_pct": 0, "top_pct": 0, "width_pct": 100, "height_pct": 4, "fill_color": "#003D7A" }
      ]
    }
  ]
}
"""


class SlideRefiner:
    def __init__(self, llm: LlmJsonClientPort):
        self._llm = llm

    @staticmethod
    def _summarize_for_refine(
        slides_boxes: list[list[dict]],
        previous: list[dict[str, Any]],
    ) -> str:
        lines: list[str] = []
        for slide in previous:
            i = slide.get("index", 0)
            use = slide.get("use", False)
            box_metas = slides_boxes[i] if i < len(slides_boxes) else []
            lines.append(
                f"슬라이드 {i} (use={use}):"
            )
            for b in slide.get("boxes", []):
                box_id = b.get("box_id")
                text = b.get("text") or ""
                # 박스 capacity 정보 (개선 판단 단서)
                meta = next(
                    (m for m in box_metas if m.get("box_id") == box_id), None
                )
                cap_info = ""
                if meta:
                    cap_info = (
                        f" [pos {meta.get('left_pct')}%,{meta.get('top_pct')}% "
                        f"size {meta.get('width_pct')}%×{meta.get('height_pct')}% "
                        f"font {meta.get('font_size_pt') or '?'}pt]"
                    )
                lines.append(
                    f"  box{box_id}{cap_info}: 현재 텍스트({len(text)}자)='{text[:100]}{'…' if len(text) > 100 else ''}'"
                )
            for j, d in enumerate(slide.get("decorations", [])):
                lines.append(
                    f"  deco{j}: type={d.get('type')} "
                    f"pos({d.get('left_pct')}%,{d.get('top_pct')}%) "
                    f"size({d.get('width_pct')}%×{d.get('height_pct')}%) "
                    f"color={d.get('fill_color') or d.get('color')}"
                )
            lines.append("")
        return "\n".join(lines)

    async def refine(
        self,
        slides_boxes: list[list[dict]],
        previous: list[dict[str, Any]],
        color_palette: list[str],
        raw_summary_for_safety: str = "",
    ) -> list[dict[str, Any]]:
        """매퍼 1차 결과(previous)를 LLM 검토 → 시각적으로 다듬은 결과 반환.

        실패하면 previous 를 그대로 반환 (안전 폴백).
        """
        snapshot = self._summarize_for_refine(slides_boxes, previous)
        palette_str = ", ".join(color_palette) if color_palette else "(제한 없음)"

        # 안전망: 환각 검증을 refiner 도 알게 하기 위해 raw 요약(짧게) 같이 전달
        safety = ""
        if raw_summary_for_safety:
            safety = (
                f"\n[raw_summary — 새 단어 추가 금지 검증용]\n"
                f"{raw_summary_for_safety[:3000]}\n"
            )

        user_prompt = (
            f"[양식 색상 팔레트] {palette_str}\n\n"
            f"[현재 매핑된 슬라이드 상태]\n{snapshot}\n"
            f"{safety}\n"
            f"위 슬라이드들을 시각적 가독성/균형/일관성 측면에서 검토 후, "
            f"동일한 JSON 형식으로 다듬어진 결과를 반환하세요. "
            f"box.text 길이 조정, bullet/라벨 포맷팅, decoration 추가 정도가 적절합니다. "
            f"raw 에 없는 새 단어/수치를 만들지 마세요."
        )

        try:
            result = await self._llm.generate_json(
                system_prompt=SYSTEM_PROMPT, user_prompt=user_prompt
            )
        except Exception as e:
            logger.exception("[SlideRefiner] LLM 호출 실패 — 1차 결과 그대로 사용: %s", e)
            return previous

        refined_slides = result.get("slides") or []
        if not refined_slides:
            logger.warning("[SlideRefiner] 빈 응답 — 1차 결과 그대로 사용")
            return previous

        # previous 와 동일한 슬라이드 수만큼 normalize
        normalized: list[dict[str, Any]] = []
        for prev in previous:
            i = prev.get("index", -1)
            match = next(
                (s for s in refined_slides if int(s.get("index", -1)) == i), None
            )
            if match is None:
                normalized.append(prev)
                continue
            # box_id 보존: refined 응답에서 같은 box_id 의 text 만 교체
            refined_boxes = {
                int(b.get("box_id", -1)): (b.get("text") or "")
                for b in (match.get("boxes") or [])
            }
            new_boxes = []
            for b in prev.get("boxes", []):
                bid = int(b.get("box_id", -1))
                new_text = refined_boxes.get(bid, b.get("text", ""))
                new_boxes.append({"box_id": bid, "text": new_text})

            decos_in = match.get("decorations") or []
            new_decos = [
                {
                    "type": (d.get("type") or "rect").lower(),
                    "left_pct": float(d.get("left_pct", 0) or 0),
                    "top_pct": float(d.get("top_pct", 0) or 0),
                    "width_pct": float(d.get("width_pct", 0) or 0),
                    "height_pct": float(d.get("height_pct", 0) or 0),
                    "fill_color": d.get("fill_color") or d.get("color"),
                    "color": d.get("color") or d.get("fill_color"),
                }
                for d in decos_in
            ] or prev.get("decorations", [])

            normalized.append(
                {
                    "index": i,
                    "use": bool(match.get("use", prev.get("use", False))),
                    "boxes": new_boxes,
                    "decorations": new_decos,
                }
            )

        used_before = sum(1 for s in previous if s.get("use"))
        used_after = sum(1 for s in normalized if s.get("use"))
        deco_before = sum(len(s.get("decorations", [])) for s in previous)
        deco_after = sum(len(s.get("decorations", [])) for s in normalized)
        logger.info(
            "[SlideRefiner] 다듬기 완료: use %d→%d, deco %d→%d",
            used_before, used_after, deco_before, deco_after,
        )
        return normalized
