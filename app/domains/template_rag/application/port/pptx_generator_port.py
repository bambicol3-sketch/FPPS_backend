from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class SlideContent:
    title: str
    body: str


@dataclass
class GeneratedPptx:
    file_path: str
    slide_count: int


class PptxGeneratorPort(ABC):
    @abstractmethod
    def generate(
        self,
        form_type: str,
        slides: list[SlideContent],
        output_dir: str,
    ) -> GeneratedPptx: ...
