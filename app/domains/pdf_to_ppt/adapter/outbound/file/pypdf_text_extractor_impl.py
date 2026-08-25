import io
import logging

from pypdf import PdfReader
from pypdf.errors import PdfReadError

from app.domains.pdf_to_ppt.application.port.pdf_text_extractor_port import (
    ExtractedPdfText,
    PdfTextExtractorPort,
)

logger = logging.getLogger(__name__)


class PypdfTextExtractorImpl(PdfTextExtractorPort):
    def extract(self, file_bytes: bytes) -> ExtractedPdfText:
        try:
            reader = PdfReader(io.BytesIO(file_bytes))
            page_count = len(reader.pages)
            pages_text = [page.extract_text() or "" for page in reader.pages]
        except (PdfReadError, ValueError, KeyError) as e:
            logger.warning("[PypdfTextExtractor] PDF 파싱 실패: %s", e)
            raise ValueError(
                "PDF 파일을 읽을 수 없습니다. 손상되었거나 지원하지 않는 형식입니다."
            ) from e

        return ExtractedPdfText(
            text="\n\n".join(pages_text),
            page_count=page_count,
        )
