from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class ExtractedPdfText:
    text: str
    page_count: int


class PdfTextExtractorPort(ABC):
    @abstractmethod
    def extract(self, file_bytes: bytes) -> ExtractedPdfText:
        """PDF 바이트에서 텍스트와 페이지 수를 추출한다."""
