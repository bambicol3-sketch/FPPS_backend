import os

from app.domains.pdf_to_ppt.application.port.pdf_text_extractor_port import (
    PdfTextExtractorPort,
)
from app.domains.pdf_to_ppt.application.port.pptx_builder_port import PptxBuilderPort
from app.domains.pdf_to_ppt.application.port.slide_outline_generator_port import (
    SlideOutlineGeneratorPort,
)
from app.domains.pdf_to_ppt.application.request.convert_pdf_request import (
    ConvertPdfRequest,
)
from app.domains.pdf_to_ppt.application.response.convert_pdf_response import (
    ConvertPdfResponse,
)
from app.domains.pdf_to_ppt.domain.service.outline_limits import (
    MAX_SLIDES,
    OutlineLimits,
)

MAX_PDF_PAGES = 30
# LLM 컨텍스트/비용 보호를 위한 truncate 상한 (문자 수 기준)
MAX_EXTRACTED_CHARS = 40_000


class ConvertPdfToPptUseCase:
    def __init__(
        self,
        text_extractor: PdfTextExtractorPort,
        outline_generator: SlideOutlineGeneratorPort,
        pptx_builder: PptxBuilderPort,
        output_dir: str,
        download_url_prefix: str,
    ):
        self._extractor = text_extractor
        self._outline_generator = outline_generator
        self._pptx_builder = pptx_builder
        self._output_dir = output_dir
        self._download_url_prefix = download_url_prefix

    async def execute(self, request: ConvertPdfRequest) -> ConvertPdfResponse:
        extracted = self._extractor.extract(request.file_bytes)

        if extracted.page_count > MAX_PDF_PAGES:
            raise ValueError(
                f"PDF 페이지 수({extracted.page_count})가 상한({MAX_PDF_PAGES}페이지)을 "
                f"초과했습니다."
            )

        text = extracted.text.strip()
        if not text:
            raise ValueError(
                "PDF에서 텍스트를 추출하지 못했습니다. 스캔 이미지로만 구성된 PDF는 "
                "지원하지 않습니다."
            )

        outline = await self._outline_generator.generate(
            text[:MAX_EXTRACTED_CHARS], max_slides=MAX_SLIDES
        )
        outline = OutlineLimits.clamp(outline)
        if not outline:
            raise ValueError("슬라이드 구조를 생성하지 못했습니다. 다시 시도해주세요.")

        deck_title = os.path.splitext(request.file_name)[0][:80] or "Presentation"

        os.makedirs(self._output_dir, exist_ok=True)
        built = self._pptx_builder.build(
            deck_title=deck_title,
            slides=outline,
            output_dir=self._output_dir,
        )

        return ConvertPdfResponse(
            file_name=built.file_name,
            download_url=f"{self._download_url_prefix}/{built.file_name}",
            slide_count=built.slide_count,
            source_page_count=extracted.page_count,
        )
