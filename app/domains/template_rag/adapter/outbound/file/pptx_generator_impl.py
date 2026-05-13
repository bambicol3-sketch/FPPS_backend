import logging
import os
from datetime import datetime
from typing import Optional

from app.domains.template_rag.application.port.pptx_generator_port import (
    GeneratedPptx,
    PptxGeneratorPort,
    SlideContent,
)

logger = logging.getLogger(__name__)


class PptxGeneratorImpl(PptxGeneratorPort):
    """python-pptx 기반 슬라이드 생성기.

    `template_path` 가 주어지면 양식 PPTX 를 베이스로 열어
    기존 슬라이드 + 디자인(테마/마스터/레이아웃)을 보존한 채
    raw data 슬라이드를 양식의 layout 으로 추가한다.
    """

    LAYOUT_TITLE_CONTENT = 1

    def generate(
        self,
        form_type: str,
        slides: list[SlideContent],
        output_dir: str,
        template_path: Optional[str] = None,
    ) -> GeneratedPptx:
        try:
            from pptx import Presentation
            from pptx.util import Pt
        except ImportError as e:
            raise RuntimeError(
                "python-pptx 가 설치되어 있지 않습니다. pip install python-pptx"
            ) from e

        os.makedirs(output_dir, exist_ok=True)

        using_template = bool(
            template_path and os.path.isfile(template_path)
        )

        if using_template:
            prs = Presentation(template_path)
            template_slide_count = len(prs.slides)
            # 양식 슬라이드 스냅샷 (제거 전 deepcopy 소스로 사용)
            template_slides_snapshot = list(prs.slides)
            self._remove_all_slides(prs)
            logger.info(
                "[TemplateRAG] 양식 템플릿 로드: %s "
                "(양식 슬라이드 %d장 → raw 청크 %d장 결과 생성, 양식 디자인 deepcopy)",
                template_path, template_slide_count, len(slides),
            )
            for raw in slides:
                idx = raw.source_slide_index
                if idx is None or idx < 0 or idx >= len(template_slides_snapshot):
                    idx = 0 if template_slides_snapshot else None
                if idx is None:
                    layout = self._pick_content_layout(prs)
                    new_slide = prs.slides.add_slide(layout)
                else:
                    source = template_slides_snapshot[idx]
                    new_slide = self._duplicate_template_slide(prs, source)

                # 양식 원본 텍스트는 모두 비우고 raw 데이터 주입
                self._clear_all_text(new_slide)
                self._inject_raw_into_shapes(new_slide, raw, Pt)
        else:
            prs = Presentation()
            cover_layout = prs.slide_layouts[0]
            cover = prs.slides.add_slide(cover_layout)
            if cover.shapes.title is not None:
                cover.shapes.title.text = f"{form_type} Report"
            if len(cover.placeholders) > 1:
                cover.placeholders[1].text = datetime.now().strftime("%Y-%m-%d")

            # 빈 PPT 모드: layout 으로 슬라이드 추가
            target_layout = self._pick_content_layout(prs)
            for slide_content in slides:
                slide = prs.slides.add_slide(target_layout)
                self._fill_slide(slide, slide_content, Pt)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_form = "".join(c if c.isalnum() else "_" for c in form_type)
        file_name = f"{safe_form}_{timestamp}.pptx"
        file_path = os.path.join(output_dir, file_name)
        prs.save(file_path)
        logger.info(
            "[TemplateRAG] PPTX 생성: %s (slides=%d, template=%s)",
            file_path, len(prs.slides), "yes" if using_template else "no",
        )

        return GeneratedPptx(file_path=file_path, slide_count=len(prs.slides))

    def generate_from_freeform_specs(
        self,
        form_type: str,
        template_path: Optional[str],
        slides: list[dict],
        output_dir: str,
    ) -> GeneratedPptx:
        """GAN Generator 결과 그대로 빈 PPT 위에 박스/도형을 자유 좌표로 그림."""
        try:
            from pptx import Presentation
            from pptx.enum.text import MSO_AUTO_SIZE, PP_ALIGN
            from pptx.util import Emu, Pt
        except ImportError as e:
            raise RuntimeError("python-pptx 미설치") from e

        os.makedirs(output_dir, exist_ok=True)
        if template_path and os.path.isfile(template_path):
            prs = Presentation(template_path)
            self._remove_all_slides(prs)
        else:
            prs = Presentation()

        sw = int(prs.slide_width or 0)
        sh = int(prs.slide_height or 0)

        # Blank layout
        blank_layout = None
        for layout in prs.slide_layouts:
            if "blank" in (layout.name or "").lower():
                blank_layout = layout
                break
        if blank_layout is None:
            blank_layout = prs.slide_layouts[-1]

        align_map = {
            "LEFT": PP_ALIGN.LEFT,
            "CENTER": PP_ALIGN.CENTER,
            "RIGHT": PP_ALIGN.RIGHT,
            "JUSTIFY": PP_ALIGN.JUSTIFY,
        }

        def _pct_to_emu(pct: float, base: int) -> int:
            return int(max(0.0, min(pct, 100.0)) / 100.0 * base)

        for slide_data in slides:
            slide = prs.slides.add_slide(blank_layout)

            # 1) decoration 먼저 (z-order 아래)
            for deco in (slide_data.get("decorations") or []):
                self._draw_decoration(slide, deco, sw, sh)

            # 2) box (텍스트)
            for box in (slide_data.get("boxes") or []):
                left = _pct_to_emu(float(box.get("left_pct", 0)), sw)
                top = _pct_to_emu(float(box.get("top_pct", 0)), sh)
                width = _pct_to_emu(float(box.get("width_pct", 0)), sw)
                height = _pct_to_emu(float(box.get("height_pct", 0)), sh)
                if width <= 0 or height <= 0:
                    continue
                text = (box.get("text") or "").strip()
                if not text:
                    continue
                try:
                    tx = slide.shapes.add_textbox(
                        Emu(left), Emu(top), Emu(width), Emu(height)
                    )
                except Exception:
                    continue
                tf = tx.text_frame
                tf.word_wrap = True
                try:
                    tf.auto_size = MSO_AUTO_SIZE.TEXT_TO_SHAPE
                except Exception:
                    pass
                font_size_pt = float(box.get("font_size_pt", 14) or 14)
                bold = bool(box.get("bold", False))
                color_hex = (box.get("color_hex") or "").lstrip("#") or None
                align = (box.get("align") or "LEFT").upper()
                for i, line in enumerate(text.split("\n")):
                    p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
                    p.text = line
                    try:
                        p.font.size = Pt(font_size_pt)
                        p.font.bold = bold
                        if color_hex:
                            from pptx.dml.color import RGBColor
                            p.font.color.rgb = RGBColor.from_string(color_hex)
                        if align in align_map:
                            p.alignment = align_map[align]
                    except Exception:
                        pass

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_form = "".join(c if c.isalnum() else "_" for c in form_type)
        file_name = f"{safe_form}_{timestamp}.pptx"
        file_path = os.path.join(output_dir, file_name)
        prs.save(file_path)
        logger.info(
            "[TemplateRAG] PPTX (freeform) 생성: %s (slides=%d)",
            file_path, len(prs.slides),
        )
        return GeneratedPptx(file_path=file_path, slide_count=len(prs.slides))

    def generate_from_box_specs(
        self,
        form_type: str,
        template_path: str,
        slides_specs: list[list[dict]],
        llm_slide_outputs: list[dict],
        output_dir: str,
        slides_background_shapes: list[list[dict]] | None = None,
    ) -> GeneratedPptx:
        """양식 박스 명세 + LLM 매핑 결과로 빈 PPT 위에 박스를 처음부터 그린다.

        - 양식 PPTX 를 베이스로 열어 슬라이드 크기/마스터/테마 유지
        - 양식 슬라이드 모두 제거
        - LLM 이 use=true 로 지정한 양식 슬라이드마다 빈 layout 위에 새 슬라이드 추가
        - 각 박스는 양식의 위치/크기/폰트를 그대로 적용한 textbox 로 새로 그림
        """
        try:
            from pptx import Presentation
            from pptx.dml.color import RGBColor
            from pptx.enum.text import MSO_AUTO_SIZE, PP_ALIGN
            from pptx.util import Emu, Pt
        except ImportError as e:
            raise RuntimeError(
                "python-pptx 가 설치되어 있지 않습니다."
            ) from e

        os.makedirs(output_dir, exist_ok=True)
        prs = Presentation(template_path)
        self._remove_all_slides(prs)

        # 'Blank' layout 찾기 (없으면 마지막 layout 사용)
        blank_layout = None
        for layout in prs.slide_layouts:
            if "blank" in (layout.name or "").lower():
                blank_layout = layout
                break
        if blank_layout is None:
            blank_layout = prs.slide_layouts[-1]

        used = 0
        align_map = {
            "LEFT": PP_ALIGN.LEFT,
            "CENTER": PP_ALIGN.CENTER,
            "RIGHT": PP_ALIGN.RIGHT,
            "JUSTIFY": PP_ALIGN.JUSTIFY,
        }
        sw = int(prs.slide_width or 0)
        sh = int(prs.slide_height or 0)

        for slide_out in llm_slide_outputs:
            if not slide_out.get("use"):
                continue
            idx = slide_out.get("index", 0)
            if idx < 0 or idx >= len(slides_specs):
                continue
            box_meta_list = slides_specs[idx]
            if not box_meta_list:
                continue

            slide = prs.slides.add_slide(blank_layout)

            # 1) 양식의 비텍스트 도형(사이드바/헤더바/배경 박스) 을 그대로 결과에 복제
            #    텍스트 색상이 어두운 배경 위에서 안 보이는 문제 해결
            if slides_background_shapes and idx < len(slides_background_shapes):
                bg_color_for_text_contrast: str | None = None
                # 가장 큰 면적의 배경 도형 색상을 텍스트 대비 색 결정용으로 사용
                bg_meta_list = slides_background_shapes[idx]
                if bg_meta_list:
                    biggest = max(
                        bg_meta_list,
                        key=lambda x: (
                            float(x.get("width_pct", 0))
                            * float(x.get("height_pct", 0))
                        ),
                    )
                    bg_color_for_text_contrast = biggest.get("fill_color")
                    # 비텍스트 도형들을 결과 슬라이드에 직접 그림
                    for bg in bg_meta_list:
                        self._draw_background_shape(slide, bg, sw, sh)
            else:
                bg_color_for_text_contrast = None

            # 2) LLM decoration 도형을 그 위에
            for deco in slide_out.get("decorations", []):
                self._draw_decoration(slide, deco, sw, sh)

            for box_out in slide_out.get("boxes", []):
                box_id = box_out.get("box_id", -1)
                text = (box_out.get("text") or "").strip()
                if not text:
                    continue
                if box_id < 0 or box_id >= len(box_meta_list):
                    continue
                meta = box_meta_list[box_id]
                try:
                    tx = slide.shapes.add_textbox(
                        Emu(meta["left_emu"]),
                        Emu(meta["top_emu"]),
                        Emu(meta["width_emu"]),
                        Emu(meta["height_emu"]),
                    )
                except Exception as e:
                    logger.debug("textbox add 실패 (skip): %s", e)
                    continue
                tf = tx.text_frame
                tf.word_wrap = True
                try:
                    tf.auto_size = MSO_AUTO_SIZE.TEXT_TO_SHAPE
                except Exception:
                    pass

                # 텍스트 색상 결정 우선순위:
                #  1) 양식 박스가 명시한 폰트 색상
                #  2) 배경(가장 큰 비텍스트 도형) 색상의 대비 색 (어두우면 흰색, 밝으면 검정)
                #  3) 기본 검정
                effective_text_color = meta.get("color_hex")
                if not effective_text_color and bg_color_for_text_contrast:
                    effective_text_color = self._contrast_text_color(
                        bg_color_for_text_contrast
                    )

                lines = text.split("\n")
                for i, line in enumerate(lines):
                    p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
                    p.text = line
                    try:
                        if meta.get("font_size_pt"):
                            p.font.size = Pt(meta["font_size_pt"])
                        if meta.get("bold") is not None:
                            p.font.bold = bool(meta["bold"])
                        if effective_text_color:
                            p.font.color.rgb = RGBColor.from_string(
                                str(effective_text_color).lstrip("#")
                            )
                        if meta.get("align") and meta["align"] in align_map:
                            p.alignment = align_map[meta["align"]]
                    except Exception:
                        pass
            used += 1

        # 결과가 비었으면 안내 슬라이드 1장만이라도 추가
        if used == 0:
            slide = prs.slides.add_slide(blank_layout)
            tx = slide.shapes.add_textbox(
                Pt(72), Pt(72), Pt(720 - 144), Pt(450)
            )
            tx.text_frame.text = (
                "raw data 에 양식 슬롯과 매칭되는 내용이 없습니다."
            )

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_form = "".join(c if c.isalnum() else "_" for c in form_type)
        file_name = f"{safe_form}_{timestamp}.pptx"
        file_path = os.path.join(output_dir, file_name)
        prs.save(file_path)
        logger.info(
            "[TemplateRAG] PPTX (box-spec) 생성: %s (slides=%d, used_template_slides=%d)",
            file_path,
            len(prs.slides),
            used,
        )
        return GeneratedPptx(file_path=file_path, slide_count=len(prs.slides))

    @staticmethod
    def _contrast_text_color(bg_hex: str | None) -> str:
        """배경 색상 hex 받아 대비되는 텍스트 색 hex 반환 (흰색 or 검정).

        luminance = 0.299*R + 0.587*G + 0.114*B
        128 이하 → 어두운 배경 → 흰색 텍스트, 그 외 → 검정
        """
        if not bg_hex:
            return "000000"
        try:
            h = str(bg_hex).lstrip("#")
            if len(h) == 6:
                r = int(h[0:2], 16)
                g = int(h[2:4], 16)
                b = int(h[4:6], 16)
                lum = 0.299 * r + 0.587 * g + 0.114 * b
                return "FFFFFF" if lum < 140 else "000000"
        except Exception:
            pass
        return "000000"

    @staticmethod
    def _draw_background_shape(
        slide, bg_meta: dict, slide_width_emu: int, slide_height_emu: int
    ) -> None:
        """양식의 비텍스트 도형(배경 사이드바/헤더바/액센트 박스) 그대로 결과에 그림."""
        from pptx.dml.color import RGBColor
        from pptx.enum.shapes import MSO_SHAPE
        from pptx.util import Emu

        def _pct_to_emu(pct: float, base: int) -> int:
            return int(max(0.0, min(pct, 100.0)) / 100.0 * base)

        left = _pct_to_emu(float(bg_meta.get("left_pct", 0)), slide_width_emu)
        top = _pct_to_emu(float(bg_meta.get("top_pct", 0)), slide_height_emu)
        width = _pct_to_emu(float(bg_meta.get("width_pct", 0)), slide_width_emu)
        height = _pct_to_emu(
            float(bg_meta.get("height_pct", 0)), slide_height_emu
        )
        if width <= 0 or height <= 0:
            return
        try:
            shape = slide.shapes.add_shape(
                MSO_SHAPE.RECTANGLE,
                Emu(left), Emu(top), Emu(width), Emu(height),
            )
            fill_hex = bg_meta.get("fill_color")
            if fill_hex:
                try:
                    shape.fill.solid()
                    shape.fill.fore_color.rgb = RGBColor.from_string(
                        str(fill_hex).lstrip("#")
                    )
                except Exception:
                    pass
            try:
                shape.line.fill.background()
            except Exception:
                pass
        except Exception as e:
            logger.debug("background shape 그리기 실패 (skip): %s", e)

    @staticmethod
    def _draw_decoration(slide, deco: dict, slide_width_emu: int, slide_height_emu: int) -> None:
        """LLM 이 알려준 decoration 명세대로 도형 그리기.

        지원 type: rect / line / circle
        위치/크기는 % 단위 → EMU 변환
        색상은 양식 팔레트의 hex 문자열
        """
        from pptx.dml.color import RGBColor
        from pptx.enum.shapes import MSO_SHAPE
        from pptx.util import Emu

        def _hex_to_rgb(value):
            if not value:
                return None
            try:
                return RGBColor.from_string(str(value).lstrip("#"))
            except Exception:
                return None

        def _pct_to_emu(pct: float, base: int) -> int:
            return int(max(0.0, min(pct, 100.0)) / 100.0 * base)

        d_type = (deco.get("type") or "rect").lower()
        left = _pct_to_emu(float(deco.get("left_pct", 0)), slide_width_emu)
        top = _pct_to_emu(float(deco.get("top_pct", 0)), slide_height_emu)
        width = _pct_to_emu(float(deco.get("width_pct", 0)), slide_width_emu)
        height = _pct_to_emu(float(deco.get("height_pct", 0)), slide_height_emu)

        try:
            if d_type == "rect":
                if width <= 0 or height <= 0:
                    return
                shape = slide.shapes.add_shape(
                    MSO_SHAPE.RECTANGLE, Emu(left), Emu(top), Emu(width), Emu(height)
                )
                rgb = _hex_to_rgb(deco.get("fill_color") or deco.get("color"))
                if rgb is not None:
                    shape.fill.solid()
                    shape.fill.fore_color.rgb = rgb
                try:
                    shape.line.fill.background()  # outline 없음
                except Exception:
                    pass
            elif d_type == "line":
                # 가로 라인: height 가 매우 작음. 세로 라인: width 가 매우 작음.
                # 면적 0 인 경우 최소 두께 부여
                if width <= 0 and height <= 0:
                    return
                if height <= 0:
                    height = max(1, int(slide_height_emu * 0.003))
                if width <= 0:
                    width = max(1, int(slide_width_emu * 0.003))
                shape = slide.shapes.add_shape(
                    MSO_SHAPE.RECTANGLE, Emu(left), Emu(top), Emu(width), Emu(height)
                )
                rgb = _hex_to_rgb(deco.get("color") or deco.get("fill_color"))
                if rgb is not None:
                    shape.fill.solid()
                    shape.fill.fore_color.rgb = rgb
                try:
                    shape.line.fill.background()
                except Exception:
                    pass
            elif d_type == "circle":
                if width <= 0 or height <= 0:
                    return
                shape = slide.shapes.add_shape(
                    MSO_SHAPE.OVAL, Emu(left), Emu(top), Emu(width), Emu(height)
                )
                rgb = _hex_to_rgb(deco.get("fill_color") or deco.get("color"))
                if rgb is not None:
                    shape.fill.solid()
                    shape.fill.fore_color.rgb = rgb
                try:
                    shape.line.fill.background()
                except Exception:
                    pass
        except Exception as e:
            logger.debug("decoration 그리기 실패 (skip): %s", e)

    @staticmethod
    def _duplicate_template_slide(prs, source_slide):
        """양식 슬라이드의 shapes 를 deepcopy 해서 새 슬라이드로 복제.

        - source 의 slide_layout 위에 새 슬라이드 생성
        - add_slide 가 자동 추가한 placeholder 는 제거 (덮어쓰기 방지)
        - source 슬라이드의 모든 shape XML 을 deepcopy 해서 새 슬라이드의 spTree 에 append
        - 주의: 이미지/차트의 part 관계(rels) 는 복제되지 않으므로 깨질 수 있음.
          텍스트/도형/색상/위치는 정상 복제됨.
        """
        from copy import deepcopy

        layout = source_slide.slide_layout
        new_slide = prs.slides.add_slide(layout)
        # auto-inserted placeholders 제거
        for ph in list(new_slide.shapes):
            try:
                ph.element.getparent().remove(ph.element)
            except Exception:
                pass
        # source shapes deepcopy 후 새 슬라이드에 추가
        for shape in source_slide.shapes:
            try:
                new_el = deepcopy(shape.element)
                new_slide.shapes._spTree.append(new_el)
            except Exception as e:
                logger.debug("shape deepcopy 실패 (skip): %s", e)
        return new_slide

    @staticmethod
    def _clear_all_text(slide) -> None:
        """슬라이드의 모든 text_frame 텍스트를 비움 (도형 자체는 보존)."""
        for shape in slide.shapes:
            if not getattr(shape, "has_text_frame", False):
                continue
            try:
                shape.text_frame.clear()
            except Exception:
                pass

    # body 텍스트 최대 길이 (도형 크기 모르므로 휴리스틱)
    BODY_MAX_CHARS = 600

    @staticmethod
    def _capture_font(text_frame):
        """텍스트 frame 첫 run 의 font 속성을 캡처해서 dict 로 반환.
        교체 시 같은 폰트로 복원하기 위함.
        """
        font_attrs: dict = {}
        try:
            paras = text_frame.paragraphs
            if not paras:
                return font_attrs
            p = paras[0]
            if p.runs:
                f = p.runs[0].font
            else:
                f = p.font
            font_attrs["size"] = f.size
            font_attrs["bold"] = f.bold
            font_attrs["italic"] = f.italic
            font_attrs["name"] = f.name
            try:
                if f.color and f.color.rgb is not None:
                    font_attrs["color"] = f.color.rgb
            except Exception:
                pass
        except Exception:
            pass
        return font_attrs

    @staticmethod
    def _apply_font(paragraph, font_attrs):
        if not font_attrs:
            return
        try:
            f = paragraph.font
            if font_attrs.get("size"):
                f.size = font_attrs["size"]
            if font_attrs.get("bold") is not None:
                f.bold = font_attrs["bold"]
            if font_attrs.get("italic") is not None:
                f.italic = font_attrs["italic"]
            if font_attrs.get("name"):
                f.name = font_attrs["name"]
            if font_attrs.get("color") is not None:
                try:
                    f.color.rgb = font_attrs["color"]
                except Exception:
                    pass
        except Exception:
            pass

    @classmethod
    def _set_text_with_fit(cls, text_frame, new_text: str, fallback_font_pt) -> None:
        """텍스트 교체 + 도형에 맞게 wrap/auto-fit + 원본 폰트 보존.

        - 원본 폰트 속성 capture
        - word_wrap 활성화
        - auto_size = SHAPE_TO_FIT_TEXT (도형이 텍스트 길이에 맞게 늘어남)
          ※ SLIDE 영역 밖으로 도형이 커질 수 있어 TEXT_TO_SHAPE 도 시도하지만
            python-pptx 는 자동 폰트 축소(TEXT_TO_SHAPE) 를 PPT 가 다시 열 때까지 계산하지 못함.
            그래서 텍스트 길이 자체를 제한하는 BODY_MAX_CHARS 로 1차 방어.
        """
        from pptx.enum.text import MSO_AUTO_SIZE

        captured = cls._capture_font(text_frame)
        text_frame.clear()
        try:
            text_frame.word_wrap = True
        except Exception:
            pass
        try:
            text_frame.auto_size = MSO_AUTO_SIZE.TEXT_TO_SHAPE
        except Exception:
            pass

        for i, line in enumerate(new_text.split("\n")):
            paragraph = (
                text_frame.paragraphs[0] if i == 0 else text_frame.add_paragraph()
            )
            paragraph.text = line
            if captured:
                cls._apply_font(paragraph, captured)
            elif fallback_font_pt is not None:
                try:
                    paragraph.font.size = fallback_font_pt
                except Exception:
                    pass

    @classmethod
    def _inject_raw_into_shapes(cls, slide, raw, Pt) -> None:
        """양식 디자인이 보존된 슬라이드에 raw 데이터 주입.

        규칙:
        - 텍스트 가능 shape 들을 위치(top)/면적 기준으로 정렬
        - 가장 위쪽(top 최소) shape → raw.title
        - 가장 큰 면적의 다른 shape → raw.body (길이 제한 + word_wrap)
        - 원본 폰트(크기/색상/굵기) 보존
        - 텍스트 shape 가 하나도 없으면 textbox fallback
        """
        from pptx.util import Inches

        text_shapes = [
            s for s in slide.shapes if getattr(s, "has_text_frame", False)
        ]

        # body 길이 제한 (도형 밖으로 넘침 방지)
        body_text = (raw.body or "")
        if len(body_text) > cls.BODY_MAX_CHARS:
            body_text = body_text[: cls.BODY_MAX_CHARS].rstrip() + "…"

        if not text_shapes:
            box = slide.shapes.add_textbox(
                Inches(0.5), Inches(1.0), Inches(9.0), Inches(5.5)
            )
            tf = box.text_frame
            tf.word_wrap = True
            full = ""
            if raw.title:
                full = raw.title[:200] + "\n\n"
            full += body_text
            cls._set_text_with_fit(tf, full, fallback_font_pt=Pt(14))
            return

        text_shapes_sorted_by_top = sorted(
            text_shapes, key=lambda s: (s.top or 0)
        )
        title_shape = (
            text_shapes_sorted_by_top[0] if len(text_shapes) >= 2 else None
        )
        body_candidates = (
            text_shapes_sorted_by_top[1:] if title_shape else text_shapes
        )

        def _area(s):
            try:
                return (s.width or 0) * (s.height or 0)
            except Exception:
                return 0

        body_shape = max(body_candidates, key=_area) if body_candidates else None

        if title_shape is not None and raw.title:
            cls._set_text_with_fit(
                title_shape.text_frame, raw.title[:200], fallback_font_pt=Pt(20)
            )

        if body_shape is not None and body_text:
            cls._set_text_with_fit(
                body_shape.text_frame, body_text, fallback_font_pt=Pt(12)
            )

    @staticmethod
    def _inject_raw_into_template_slides(prs, raw_slides: list, Pt) -> None:
        """양식 슬라이드 N장을 그대로 유지하면서, 각 슬라이드의 placeholder 만 교체.

        - title placeholder → raw_slide.title
        - 그 외 첫 본문 placeholder → raw_slide.body
        - 도형/textbox/이미지/배경 등 양식의 시각 요소는 손대지 않음
        - raw 데이터가 양식 슬라이드 수보다 적으면 round-robin
        - raw 데이터가 양식 슬라이드 수보다 많으면 앞에서부터 매칭
        """
        if not raw_slides:
            return
        for i, slide in enumerate(prs.slides):
            if i >= len(raw_slides):
                break  # raw 가 부족하면 나머지 양식 슬라이드는 원본 보존
            raw = raw_slides[i]
            # 빈 SlideContent (title=""/body="") 는 매칭 거리 임계값 초과 케이스 → 원본 보존
            if not raw.title and not raw.body:
                continue
            # title placeholder
            try:
                if slide.shapes.title is not None and raw.title:
                    slide.shapes.title.text = raw.title[:200]
            except Exception:
                pass
            if not raw.body:
                continue
            # 첫 본문 placeholder (title 아닌 텍스트 placeholder)
            body_ph = None
            for ph in slide.placeholders:
                try:
                    if ph.placeholder_format.idx == 0:
                        continue  # title
                except Exception:
                    continue
                if not getattr(ph, "has_text_frame", False):
                    continue
                body_ph = ph
                break
            if body_ph is None:
                continue
            tf = body_ph.text_frame
            tf.clear()
            for li, line in enumerate(raw.body.split("\n")):
                paragraph = tf.paragraphs[0] if li == 0 else tf.add_paragraph()
                paragraph.text = line

    @staticmethod
    def _remove_all_slides(prs) -> None:
        """양식 PPTX 의 모든 슬라이드를 제거하되 슬라이드 마스터/레이아웃/테마는 보존.

        python-pptx 가 슬라이드 삭제 public API 를 제공하지 않아 XML 수준에서 처리한다.
        - sldIdLst 에서 sld 엔트리 제거 (presentation.xml.rels 의 관계도 정리)
        """
        slide_id_list = prs.slides._sldIdLst
        rels = prs.part.rels
        for sld in list(slide_id_list):
            rId = sld.get(
                "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
            )
            slide_id_list.remove(sld)
            if rId and rId in rels:
                try:
                    prs.part.drop_rel(rId)
                except Exception:
                    pass

    @staticmethod
    def _pick_content_layout(prs):
        """양식 PPTX 의 layout 중 'content' 성격에 가까운 것을 선택.

        - 이름에 'content'/'body'/'text' 포함된 layout 우선
        - 못 찾으면 index 1 (대부분 PowerPoint 기본 'Title and Content')
        - 그것도 없으면 첫 번째
        """
        keywords = ("content", "body", "text", "본문", "내용")
        for layout in prs.slide_layouts:
            name = (layout.name or "").lower()
            if any(k in name for k in keywords):
                return layout
        if len(prs.slide_layouts) > 1:
            return prs.slide_layouts[1]
        return prs.slide_layouts[0]

    @staticmethod
    def _fill_slide(slide, slide_content: SlideContent, Pt) -> None:
        if slide.shapes.title is not None:
            slide.shapes.title.text = slide_content.title[:120]

        body_placeholder = None
        for ph in slide.placeholders:
            # title (idx=0) 이 아닌 첫 텍스트 placeholder 사용
            if ph.placeholder_format.idx != 0 and ph.has_text_frame:
                body_placeholder = ph
                break
        if body_placeholder is None:
            return

        tf = body_placeholder.text_frame
        tf.clear()
        for i, line in enumerate(slide_content.body.split("\n")):
            paragraph = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
            paragraph.text = line
            paragraph.font.size = Pt(14)
