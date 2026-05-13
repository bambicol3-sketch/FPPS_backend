from abc import ABC, abstractmethod
from dataclasses import dataclass


from typing import Optional


@dataclass
class SlideContent:
    title: str
    body: str
    source_slide_index: Optional[int] = None  # 양식 모드에서 차용할 양식 슬라이드 index


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
        template_path: "str | None" = None,
    ) -> GeneratedPptx: ...

    @abstractmethod
    def generate_from_freeform_specs(
        self,
        form_type: str,
        template_path: "str | None",
        slides: list[dict],
        output_dir: str,
    ) -> GeneratedPptx:
        """GAN Generator 가 만든 자유 박스 명세(slides[].boxes[], decorations[]) 로 PPT 생성.

        template_path 가 있으면 슬라이드 크기/마스터/테마 보존. 박스/도형은 자유로 그림.
        """

    @abstractmethod
    def generate_from_box_specs(
        self,
        form_type: str,
        template_path: str,
        slides_specs: list[list[dict]],
        llm_slide_outputs: list[dict],
        output_dir: str,
        slides_background_shapes: list[list[dict]] | None = None,
    ) -> GeneratedPptx:
        """양식 박스 명세 + LLM 매핑 결과로 빈 PPT 위에 박스 처음부터 그림.

        slides_background_shapes: 슬라이드별 비텍스트 도형 메타(위치/크기/fill_color).
        주어지면 결과 슬라이드에 배경 도형도 함께 복제 → 양식의 어두운 배경/사이드바 보존.
        """
