import logging
import os
from datetime import datetime

from app.domains.template_rag.application.port.pptx_generator_port import (
    GeneratedPptx,
    PptxGeneratorPort,
    SlideContent,
)

logger = logging.getLogger(__name__)


class PptxGeneratorImpl(PptxGeneratorPort):
    """python-pptx 기반 기본 슬라이드 생성기.

    슬라이드 구조: 표지(0) + 슬라이드별 (제목 + 본문) layout(1).
    양식별로 다른 layout 이 필요하면 _layout_for_form 분기로 확장한다.
    """

    LAYOUT_TITLE_CONTENT = 1

    def generate(
        self,
        form_type: str,
        slides: list[SlideContent],
        output_dir: str,
    ) -> GeneratedPptx:
        try:
            from pptx import Presentation
            from pptx.util import Pt
        except ImportError as e:
            raise RuntimeError(
                "python-pptx 가 설치되어 있지 않습니다. pip install python-pptx"
            ) from e

        os.makedirs(output_dir, exist_ok=True)
        prs = Presentation()

        cover_layout = prs.slide_layouts[0]
        cover = prs.slides.add_slide(cover_layout)
        if cover.shapes.title is not None:
            cover.shapes.title.text = f"{form_type} Report"
        if len(cover.placeholders) > 1:
            cover.placeholders[1].text = datetime.now().strftime("%Y-%m-%d")

        for slide_content in slides:
            layout = prs.slide_layouts[self.LAYOUT_TITLE_CONTENT]
            slide = prs.slides.add_slide(layout)
            if slide.shapes.title is not None:
                slide.shapes.title.text = slide_content.title[:120]

            body_placeholder = None
            for ph in slide.placeholders:
                if ph.placeholder_format.idx == 1:
                    body_placeholder = ph
                    break
            if body_placeholder is None:
                continue

            tf = body_placeholder.text_frame
            tf.clear()
            for i, line in enumerate(slide_content.body.split("\n")):
                paragraph = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
                paragraph.text = line
                paragraph.font.size = Pt(14)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_form = "".join(c if c.isalnum() else "_" for c in form_type)
        file_name = f"{safe_form}_{timestamp}.pptx"
        file_path = os.path.join(output_dir, file_name)
        prs.save(file_path)
        logger.info(
            "[TemplateRAG] PPTX 생성: %s (slides=%d)", file_path, len(prs.slides)
        )

        return GeneratedPptx(file_path=file_path, slide_count=len(prs.slides))
