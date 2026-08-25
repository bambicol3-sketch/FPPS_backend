from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.domains.pdf_to_ppt.domain.value_object.slide_outline import SlideOutline


@dataclass
class BuiltPptx:
    file_path: str
    file_name: str
    slide_count: int


class PptxBuilderPort(ABC):
    @abstractmethod
    def build(
        self,
        deck_title: str,
        slides: list[SlideOutline],
        output_dir: str,
    ) -> BuiltPptx:
        """슬라이드 개요로 기본 테마 PPTX 파일을 생성한다."""
