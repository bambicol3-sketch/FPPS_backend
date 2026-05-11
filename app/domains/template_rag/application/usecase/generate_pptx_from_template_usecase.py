import logging
import os

from app.domains.template_rag.application.port.embedding_port import EmbeddingPort
from app.domains.template_rag.application.port.file_reader_port import FileReaderPort
from app.domains.template_rag.application.port.pptx_generator_port import (
    PptxGeneratorPort,
    SlideContent,
)
from app.domains.template_rag.application.port.template_chunk_repository_port import (
    TemplateChunkRepositoryPort,
)
from app.domains.template_rag.application.request.generate_pptx_request import (
    GeneratePptxRequest,
)
from app.domains.template_rag.application.response.generate_pptx_response import (
    GeneratePptxResponse,
)
from app.domains.template_rag.domain.service.chunking_service import ChunkingService
from app.domains.template_rag.domain.value_object.form_type import FormType

logger = logging.getLogger(__name__)


class GeneratePptxFromTemplateUseCase:
    def __init__(
        self,
        repository: TemplateChunkRepositoryPort,
        embedding: EmbeddingPort,
        file_reader: FileReaderPort,
        pptx_generator: PptxGeneratorPort,
        output_dir: str,
        download_url_prefix: str = "/api/v1/template-rag/download",
    ):
        self._repo = repository
        self._embedding = embedding
        self._reader = file_reader
        self._pptx = pptx_generator
        self._output_dir = output_dir
        self._download_url_prefix = download_url_prefix

    async def execute(
        self, request: GeneratePptxRequest
    ) -> GeneratePptxResponse:
        form_type = FormType.from_string(request.form_type)

        if not os.path.isdir(request.raw_data_dir):
            raise ValueError(
                f"raw data 폴더가 존재하지 않습니다: {request.raw_data_dir}"
            )

        sheet_size = await self._repo.count_by_form_type(form_type.value)
        if sheet_size == 0:
            raise ValueError(
                f"양식 sheet '{form_type.value}' 에 저장된 데이터가 없습니다. "
                f"먼저 /api/v1/template-rag/ingest 로 양식을 등록하세요."
            )

        raw_files = self._reader.collect(request.raw_data_dir)
        if not raw_files:
            raise ValueError(
                f"raw data 폴더가 비어 있거나 지원 확장자 파일이 없습니다: {request.raw_data_dir}"
            )

        slides: list[SlideContent] = []
        total_referenced = 0

        for raw in raw_files:
            raw_chunks = ChunkingService.split(raw.text, chunk_size=800, overlap=0)
            if not raw_chunks:
                continue
            query = raw_chunks[0]
            query_emb = await self._embedding.generate(query)
            template_chunks = await self._repo.search_similar(
                form_type=form_type.value,
                embedding=query_emb,
                limit=request.top_k,
            )
            total_referenced += len(template_chunks)

            template_section = "\n".join(
                f"• {c.chunk_text[:300]}" for c in template_chunks[:3]
            ) or "(템플릿 매칭 없음)"

            body = (
                f"[원본] {raw.file_name}\n\n"
                f"{raw_chunks[0][:600]}\n\n"
                f"--- 템플릿 매칭 ---\n{template_section}"
            )
            slides.append(SlideContent(title=raw.file_name, body=body))

        if not slides:
            raise ValueError(
                "생성할 슬라이드가 없습니다. raw data 파일에서 텍스트를 추출하지 못했습니다."
            )

        os.makedirs(self._output_dir, exist_ok=True)
        result = self._pptx.generate(
            form_type=form_type.value,
            slides=slides,
            output_dir=self._output_dir,
        )

        file_name = os.path.basename(result.file_path)
        download_url = f"{self._download_url_prefix}/{file_name}"

        return GeneratePptxResponse(
            form_type=form_type.value,
            sheet_name=form_type.value,
            file_path=result.file_path,
            download_url=download_url,
            slide_count=result.slide_count,
            files_read=len(raw_files),
            chunks_referenced=total_referenced,
        )
