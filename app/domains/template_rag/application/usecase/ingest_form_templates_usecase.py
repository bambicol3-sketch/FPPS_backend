import logging
import os
from typing import Optional

from app.domains.template_rag.application.cache.parse_cache import ParseCache
from app.domains.template_rag.application.config.form_type_mapping import (
    FormTypeMapping,
    default_mapping,
)
from app.domains.template_rag.application.port.embedding_port import EmbeddingPort
from app.domains.template_rag.application.port.file_reader_port import FileReaderPort
from app.domains.template_rag.application.port.llm_json_client_port import (
    LlmJsonClientPort,
)
from app.domains.template_rag.application.port.template_chunk_repository_port import (
    TemplateChunkRepositoryPort,
)
from app.domains.template_rag.application.service.template_parser import (
    TemplateParser,
)
from app.domains.template_rag.application.request.ingest_templates_request import (
    IngestTemplatesRequest,
)
from app.domains.template_rag.application.response.ingest_templates_response import (
    IngestTemplatesResponse,
    SheetIngestResult,
)
from app.domains.template_rag.domain.entity.template_chunk import TemplateChunk
from app.domains.template_rag.domain.service.chunking_service import ChunkingService
from app.domains.template_rag.domain.value_object.form_type import FormType

logger = logging.getLogger(__name__)


class IngestFormTemplatesUseCase:
    def __init__(
        self,
        repository: TemplateChunkRepositoryPort,
        embedding: EmbeddingPort,
        file_reader: FileReaderPort,
        mapping: Optional[FormTypeMapping] = None,
        llm_json: Optional[LlmJsonClientPort] = None,
    ):
        self._repo = repository
        self._embedding = embedding
        self._reader = file_reader
        self._mapping = mapping
        self._llm_json = llm_json
        self._template_parser = (
            TemplateParser(llm_json) if llm_json else None
        )

    async def execute(
        self, request: IngestTemplatesRequest
    ) -> IngestTemplatesResponse:
        mapping = self._resolve_mapping(request)

        sheet_results: list[SheetIngestResult] = []
        total_files = 0
        total_chunks = 0

        for config in mapping.items():
            result = await self._process_sheet(
                form_type=config.form_type.value,
                sheet_name=config.sheet_name,
                folder_path=config.folder_path,
            )
            sheet_results.append(result)
            total_files += result.files_processed
            total_chunks += result.chunks_created

        return IngestTemplatesResponse(
            sheets=sheet_results,
            total_files_processed=total_files,
            total_chunks_created=total_chunks,
        )

    def _resolve_mapping(
        self, request: IngestTemplatesRequest
    ) -> FormTypeMapping:
        if request.base_dir is None and not request.overrides:
            if self._mapping is not None:
                return self._mapping
            raise ValueError("base_dir 또는 overrides 가 필요합니다.")

        mapping = default_mapping(request.base_dir or "")
        for key, folder in request.overrides.items():
            form_type = FormType.from_string(key)
            mapping.register(form_type, folder_path=folder)
        return mapping

    async def _process_sheet(
        self,
        form_type: str,
        sheet_name: str,
        folder_path: str,
    ) -> SheetIngestResult:
        if not folder_path or not os.path.isdir(folder_path):
            logger.warning(
                "[Ingest] folder 없음: %s (form_type=%s)", folder_path, form_type
            )
            return SheetIngestResult(
                form_type=form_type,
                sheet_name=sheet_name,
                folder_path=folder_path,
                files_processed=0,
                files_failed=[],
                chunks_created=0,
            )

        files = self._reader.collect(folder_path)
        processed = 0
        failed: list[str] = []
        chunks_created = 0

        for extracted in files:
            try:
                # === 임베딩 전 양식 파싱 (PPTX 만, 캐시 활용) ===
                if (
                    self._template_parser is not None
                    and extracted.file_path.lower().endswith(".pptx")
                ):
                    cache_key = f"template_parse:{form_type}:{extracted.file_hash}"
                    if ParseCache.get(cache_key) is None:
                        try:
                            from app.domains.template_rag.application.usecase.generate_pptx_from_template_usecase import (
                                GeneratePptxFromTemplateUseCase as _UC,
                            )
                            visual = _UC._extract_template_visual_meta(
                                extracted.file_path
                            )
                            parsed = await self._template_parser.parse(
                                slides_boxes=visual["slides_boxes"],
                                slides_shapes=visual["slides_shapes"],
                                color_palette=visual["color_palette"],
                            )
                            ParseCache.set(
                                cache_key,
                                {"visual": visual, "parsed": parsed},
                            )
                            logger.info(
                                "[Ingest] 양식 파싱 캐시 저장: %s",
                                extracted.file_path,
                            )
                        except Exception as e:
                            logger.warning(
                                "[Ingest] 양식 파싱 실패 (계속 진행): %s",
                                e,
                            )

                existing_hash = await self._repo.get_file_hash(
                    form_type, extracted.file_path
                )
                if existing_hash == extracted.file_hash:
                    processed += 1
                    continue

                if existing_hash is not None:
                    await self._repo.delete_by_file(form_type, extracted.file_path)

                chunks_text = ChunkingService.split(extracted.text)
                if not chunks_text:
                    processed += 1
                    continue

                embeddings = await self._embedding.generate_batch(chunks_text)
                chunks = [
                    TemplateChunk(
                        form_type=form_type,
                        file_path=extracted.file_path,
                        file_name=extracted.file_name,
                        file_hash=extracted.file_hash,
                        chunk_index=i,
                        chunk_text=text,
                        chunk_hash=ChunkingService.hash_text(text),
                        embedding=embedding,
                    )
                    for i, (text, embedding) in enumerate(
                        zip(chunks_text, embeddings)
                    )
                ]
                inserted = await self._repo.upsert_bulk(chunks)
                chunks_created += inserted
                processed += 1
            except Exception as e:
                logger.exception(
                    "[Ingest] %s 처리 실패: %s", extracted.file_path, e
                )
                failed.append(extracted.file_path)

        return SheetIngestResult(
            form_type=form_type,
            sheet_name=sheet_name,
            folder_path=folder_path,
            files_processed=processed,
            files_failed=failed,
            chunks_created=chunks_created,
        )
