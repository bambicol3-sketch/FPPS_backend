import json
import logging
from typing import Any

from app.domains.template_rag.application.port.llm_json_client_port import (
    LlmJsonClientPort,
)

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """당신은 raw data 를 PPT 양식의 디자인 의도에 맞춰 재구성하고
**시각적으로 정리·꾸며주는** 전문 디자이너 + 데이터 분석가입니다.

[★★최우선 규칙 — 환각 절대 금지★★]
1. 결과 box.text 의 **모든 단어/수치/용어/고유명사/숫자** 는 반드시 아래 두 출처 중 하나에 명시되어야 한다:
   - 원본 raw text
   - 또는 parsed raw 의 key_values / sections / bullets / numbers
   이 외부 지식, 추측, 일반 비즈 용어는 **금지**.
2. 입력에는 양식 슬라이드의 slot_name/purpose(슬롯 의미 라벨)만 들어있다. 양식의 원문 텍스트는 입력에 없으므로 양식 텍스트를 추측해 내지 말 것.
3. 일반 비즈 프레임워크 단어(SWOT, PEST, 4P, TAM/SAM/SOM, Funnel, OKR, Roadmap, KPI 등) 는 **raw 에 그 단어가 그대로 등장하지 않으면 사용 금지**.
4. 양식 박스 slot 의미는 raw 와 어울리지 않을 수 있다. 어울리는 raw 가 없으면 그 박스는 text="". 슬라이드 전체가 어울리지 않으면 use=false.
5. 한 글자라도 raw 출처에 없는 단어가 들어가면 잘못된 결과. 의심스러우면 비울 것.


[입력 정보]
- 양식 슬라이드들의 텍스트 박스 명세 (위치·크기·폰트·원본 텍스트)
- 양식 슬라이드들의 비텍스트 도형 명세 (위치·크기·색상)  ← 양식의 시각 스타일 단서
- 양식의 색상 팔레트 (자주 쓰이는 fill 색상 hex)
- 양식의 폰트 색상 / 폰트 크기 팔레트
- raw data 텍스트

[해야 할 일]
1. 양식 박스의 위치/크기/폰트/원본 텍스트로 박스의 의도(슬롯 의미)를 파악.
2. raw data 에서 그 의도에 맞는 부분을 골라 **박스 크기에 맞는 길이**로 텍스트 작성.
3. raw data 의 내용을 **단순 텍스트 나열이 아니라 시각적으로 정리**해서 작성:
   - 핵심 수치/지표는 짧고 굵게 (한 박스에 한 줄)
   - 항목은 bullet (•) 또는 번호 (1. 2. 3.) 로 구분
   - 비교 가능한 데이터는 라벨과 값을 ' : ' 로 정렬 (예: "매출 : 12.3억")
   - 결론/요약은 간결한 한 두 줄
4. 양식의 **시각 스타일(헤더 바, 액센트 라인, 강조 색상 등)** 을 결과 슬라이드에도 재현하도록
   각 슬라이드의 decoration 도형을 명세로 출력. 양식이 쓰는 색상 팔레트의 색만 사용.
5. raw 와 무관한 슬라이드 전체는 use=false.

[박스 capacity 추정]
- 한 박스에 들어갈 글자 수 ≈ (width_pct × height_pct × 8) / (font_size_pt or 14)
- 텍스트는 capacity 의 70% 이내로 짧게.

[decoration 종류]
- "rect" : 사각형 (header bar, accent box). fill_color 필수.
- "line" : 가로/세로 라인 (구분선). color 필수. width_pct 또는 height_pct 중 하나가 0~1 사이면 라인.
- "circle": 원형 마커/아이콘 placeholder. fill_color 필수.
- 모든 도형 위치/크기는 % (0~100) 단위. 슬라이드 경계 안쪽에 배치.
- color/fill_color 는 hex 문자열 ("#003D7A" 또는 "003D7A"). 반드시 양식 color_palette 중 하나.
- 슬라이드당 decoration 1~4개. 과하지 않게.
- 박스(텍스트) 위에 deco 를 올려 가리지 않도록 텍스트 박스 영역은 피할 것.

[응답 형식 — JSON 객체 1개만]
{
  "slides": [
    {
      "index": 0,
      "use": true,
      "boxes": [
        { "box_id": 0, "text": "Q4 매출 보고서" },
        { "box_id": 1, "text": "• 매출 : 12.3억\\n• 전분기 대비 +8%\\n• 핵심 동력 : 신제품 A" }
      ],
      "decorations": [
        { "type": "rect", "left_pct": 0, "top_pct": 0, "width_pct": 100, "height_pct": 4, "fill_color": "#003D7A" },
        { "type": "line", "left_pct": 8, "top_pct": 22, "width_pct": 84, "height_pct": 0.3, "color": "#888888" }
      ]
    },
    { "index": 1, "use": false, "boxes": [], "decorations": [] }
  ]
}

라이팅 톤: 한국어, 간결, 비즈니스 보고서 어조. raw 가 영어면 자연스러운 한국어로 옮김.
없는 사실을 만들지 말 것. raw 에 있는 사실/수치만 사용.
"""


class RawDataMapper:
    def __init__(self, llm: LlmJsonClientPort):
        self._llm = llm

    @staticmethod
    def _summarize_slide_for_llm(
        slide_idx: int,
        boxes: list[dict],
        shapes: list[dict],
    ) -> str:
        """양식 박스 명세를 LLM 에 전달용 문자열로 요약.

        ⚠️ 양식의 original_text(원본 텍스트) 는 의도적으로 노출하지 않는다.
            노출하면 LLM 이 그 문구를 결과에 그대로/변형해서 출력하는 환각이 발생.
            슬롯 의미는 parsed_template (slot_name/purpose) 로 별도 전달.
        """
        if not boxes and not shapes:
            return f"슬라이드 {slide_idx}: (빈 슬라이드)"
        lines = [f"슬라이드 {slide_idx}:"]
        for b in boxes:
            font = b.get("font_size_pt") or 14
            bold = "bold" if b.get("bold") else "regular"
            color = b.get("color_hex") or "default"
            align = b.get("align") or "default"
            # 박스 크기 기반 capacity 추정값을 같이 알려줘 LLM 이 길이 조절하기 쉽게
            cap = max(
                20,
                int(
                    (float(b.get("width_pct", 0)) * float(b.get("height_pct", 0)) * 8)
                    / max(font, 8)
                ),
            )
            lines.append(
                f"  텍스트박스{b['box_id']}: pos({b['left_pct']}%,{b['top_pct']}%) "
                f"size({b['width_pct']}%×{b['height_pct']}%) "
                f"font {font}pt {bold} {color} align={align} "
                f"max≈{cap}자"
            )
        for i, s in enumerate(shapes):
            lines.append(
                f"  비텍스트도형{i}: type={s.get('shape_type')} "
                f"pos({s['left_pct']}%,{s['top_pct']}%) "
                f"size({s['width_pct']}%×{s['height_pct']}%) "
                f"fill={s.get('fill_color') or '-'}"
            )
        return "\n".join(lines)

    async def map_raw_to_box_specs(
        self,
        slides_boxes: list[list[dict]],
        slides_shapes: list[list[dict]],
        color_palette: list[str],
        font_palette: list[str],
        font_size_palette: list[float],
        raw_text: str,
        parsed_template: dict | None = None,
        parsed_raw: dict | None = None,
    ) -> list[dict[str, Any]]:
        """양식/raw 파싱 결과 + 박스 명세 → 슬라이드별 (use, boxes, decorations).

        - parsed_template: TemplateParser 결과 (슬라이드 role/slots/style_notes 등)
        - parsed_raw: RawDataParser 결과 (sections/key_values/bullets/numbers/...)
        - raw_text: 파싱 못한 경우 폴백용 원문
        """
        import json as _json

        slide_summaries = "\n\n".join(
            self._summarize_slide_for_llm(
                i, slides_boxes[i] if i < len(slides_boxes) else [],
                slides_shapes[i] if i < len(slides_shapes) else [],
            )
            for i in range(max(len(slides_boxes), len(slides_shapes)))
        )

        palette_str = ", ".join(color_palette) if color_palette else "(자유롭게)"
        font_palette_str = ", ".join(font_palette) if font_palette else "(default)"
        font_size_str = (
            ", ".join(f"{s}pt" for s in font_size_palette)
            if font_size_palette
            else "(default)"
        )

        # 파싱된 양식 구조 — 의미 라벨(slot_name/purpose/role)만 노출.
        # raw 가 아닌 양식 원문이 LLM 입력으로 새는 것을 막기 위해 다른 자유 텍스트 필드는 제외.
        if parsed_template:
            slim_slides = []
            for s in parsed_template.get("slides") or []:
                slim_slides.append(
                    {
                        "index": s.get("index"),
                        "role": s.get("role"),
                        "design_pattern": s.get("design_pattern"),
                        "slots": [
                            {
                                "box_id": slot.get("box_id"),
                                "slot_name": slot.get("slot_name"),
                                "purpose": slot.get("purpose"),
                            }
                            for slot in (s.get("slots") or [])
                        ],
                    }
                )
            template_struct_txt = _json.dumps(slim_slides, ensure_ascii=False)[:5000]
        else:
            template_struct_txt = "(양식 파싱 결과 없음)"

        # 파싱된 raw 데이터
        if parsed_raw:
            raw_struct_txt = _json.dumps(parsed_raw, ensure_ascii=False)[:8000]
        else:
            # raw_text 폴백 (파싱 없을 때만)
            max_raw_chars = 8000
            if len(raw_text) > max_raw_chars:
                raw_text = raw_text[:max_raw_chars] + "\n...(이하 생략)"
            raw_struct_txt = f"(파싱 결과 없음 — 원문)\n{raw_text}"

        user_prompt = (
            f"[양식 색상 팔레트] {palette_str}\n"
            f"[양식 폰트 색상] {font_palette_str}\n"
            f"[양식 폰트 크기] {font_size_str}\n\n"
            f"[양식 슬라이드 박스 명세]\n{slide_summaries}\n\n"
            f"[양식 슬라이드 파싱 구조 (slots/roles)]\n{template_struct_txt}\n\n"
            f"[raw 파싱 결과]\n{raw_struct_txt}\n\n"
            f"각 양식 슬라이드의 boxes 와 decorations 를 작성. "
            f"slots 정보(slot_name/purpose) 와 raw 의 key_values/sections/bullets/numbers 를 매칭해서 "
            f"슬라이드별로 의미 맞춤 채움. raw 와 무관 슬라이드는 use=false. "
            f"라벨-값 / bullet / 간결한 수치로 시각적으로 정리."
        )

        try:
            result = await self._llm.generate_json(
                system_prompt=SYSTEM_PROMPT,
                user_prompt=user_prompt,
            )
        except Exception as e:
            logger.exception("[RawDataMapper] LLM 호출 실패: %s", e)
            result = {}

        raw_slides = result.get("slides") or []

        # 후처리 안전망: 결과 텍스트의 영문/숫자 토큰이 raw_text 에 등장하는지 검증.
        # 등장률이 너무 낮으면 환각 가능성 → 그 박스 text 를 비움.
        # 한국어 위주 raw 에서도 영어 약어(예: TAM, SAM, SOM)는 raw 에 그대로 있어야 통과.
        import re as _re

        raw_tokens_lower = set()
        if raw_text:
            for tok in _re.findall(r"[A-Za-z0-9가-힣]+", raw_text):
                raw_tokens_lower.add(tok.lower())
        if parsed_raw:
            try:
                raw_struct_str = _json.dumps(parsed_raw, ensure_ascii=False)
                for tok in _re.findall(r"[A-Za-z0-9가-힣]+", raw_struct_str):
                    raw_tokens_lower.add(tok.lower())
            except Exception:
                pass

        def _looks_hallucinated(text: str) -> bool:
            """영문 약어(2~6자 대문자 토큰)가 raw 에 없으면 환각으로 간주."""
            if not text:
                return False
            for tok in _re.findall(r"[A-Z]{2,6}", text):
                if tok.lower() not in raw_tokens_lower:
                    return True
            return False

        normalized: list[dict[str, Any]] = []
        for i in range(len(slides_boxes)):
            match = next(
                (s for s in raw_slides if int(s.get("index", -1)) == i), None
            )
            if match is None:
                normalized.append(
                    {"index": i, "use": False, "boxes": [], "decorations": []}
                )
                continue
            use = bool(match.get("use", False))
            boxes_in = match.get("boxes") or []
            decos_in = match.get("decorations") or []

            cleaned_boxes = []
            for b in boxes_in:
                txt = (b.get("text") or "")
                if _looks_hallucinated(txt):
                    logger.warning(
                        "[RawDataMapper] 환각 의심 텍스트 제거 (slide=%d box=%s): %s",
                        i, b.get("box_id"), txt[:80],
                    )
                    txt = ""
                cleaned_boxes.append(
                    {
                        "box_id": int(b.get("box_id", -1)),
                        "text": txt,
                    }
                )

            normalized.append(
                {
                    "index": i,
                    "use": use,
                    "boxes": cleaned_boxes,
                    "decorations": [
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
                    ],
                }
            )

        used_count = sum(1 for s in normalized if s["use"])
        deco_count = sum(len(s["decorations"]) for s in normalized)
        logger.info(
            "[RawDataMapper] %d장 분석 → 사용 %d장, decoration %d개 생성",
            len(normalized), used_count, deco_count,
        )
        return normalized
