from abc import ABC, abstractmethod

from app.domains.pdf_to_ppt.domain.value_object.slide_outline import SlideOutline


class SlideOutlineGeneratorPort(ABC):
    @abstractmethod
    async def generate(self, text: str, max_slides: int) -> list[SlideOutline]:
        """추출된 문서 텍스트를 분석해 슬라이드 제목+불릿 개요를 생성한다."""
