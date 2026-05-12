import logging
import os
from typing import Optional

from app.domains.template_rag.application.port.embedding_port import EmbeddingPort
from app.domains.template_rag.application.port.file_reader_port import FileReaderPort
from app.domains.template_rag.application.port.llm_json_client_port import (
    LlmJsonClientPort,
)
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
from app.domains.template_rag.application.cache.parse_cache import ParseCache
from app.domains.template_rag.application.service.raw_data_mapper import (
    RawDataMapper,
)
from app.domains.template_rag.application.service.raw_data_parser import (
    RawDataParser,
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
        download_url_prefix: str = "/api/v1/rag/download",
        llm_json: Optional[LlmJsonClientPort] = None,
    ):
        self._repo = repository
        self._embedding = embedding
        self._reader = file_reader
        self._pptx = pptx_generator
        self._output_dir = output_dir
        self._download_url_prefix = download_url_prefix
        self._llm_json = llm_json
        self._raw_mapper = RawDataMapper(llm_json) if llm_json else None
        # 양식 파싱은 ingest 단계에서만. PPT 생성 시에는 raw 파싱만.
        self._raw_parser = RawDataParser(llm_json) if llm_json else None

    # 매칭 distance 임계값 (text-embedding-3-small cosine distance 기준)
    # 0 = 동일, 1 = 무관. 0.7 이상은 매칭 의미 없음으로 간주 → 원본 슬라이드 유지.
    MATCH_DISTANCE_THRESHOLD = 0.7

    @staticmethod
    def _find_template_cache_key(
        template_path: str, form_type: str
    ) -> Optional[str]:
        """ingest 시 저장한 양식 파싱 캐시의 key 찾기.

        key 포맷: 'template_parse:<form_type>:<file_hash>'
        파일 내용으로 sha256 계산해서 일치하는 key 반환.
        """
        import hashlib
        try:
            with open(template_path, "rb") as f:
                file_hash = hashlib.sha256(f.read()).hexdigest()
            candidate = f"template_parse:{form_type}:{file_hash}"
            if ParseCache.get(candidate) is not None:
                return candidate
        except Exception:
            pass
        return None

    @staticmethod
    def _extract_template_visual_meta(template_path: str) -> dict:
        """양식 PPTX 의 시각 메타데이터를 한 번에 추출.

        반환:
        - slide_width_emu / slide_height_emu
        - slides_boxes : 슬라이드별 텍스트 박스 명세 list
        - slides_shapes: 슬라이드별 비텍스트 도형 명세 list (위치/크기/색상)
        - color_palette: 자주 쓰이는 fill 색상 hex 상위 N개
        - font_palette : 자주 쓰이는 폰트 size,color hex pair
        """
        from pptx import Presentation

        prs = Presentation(template_path)
        sw = int(prs.slide_width or 1)
        sh = int(prs.slide_height or 1)

        def _pct(emu: int, base: int) -> float:
            return round(emu / base * 100, 2) if base else 0.0

        slides_boxes: list[list[dict]] = []
        slides_shapes: list[list[dict]] = []
        fill_color_counter: dict[str, int] = {}
        font_color_counter: dict[str, int] = {}
        font_sizes: dict[float, int] = {}

        for slide in prs.slides:
            boxes: list[dict] = []
            shapes_meta: list[dict] = []
            for shape in slide.shapes:
                pos_info = {
                    "left_pct": _pct(int(shape.left or 0), sw),
                    "top_pct": _pct(int(shape.top or 0), sh),
                    "width_pct": _pct(int(shape.width or 0), sw),
                    "height_pct": _pct(int(shape.height or 0), sh),
                }
                # 비텍스트 도형 = 시각 장식 후보
                is_text_shape = getattr(shape, "has_text_frame", False) and (
                    (shape.text_frame.text or "").strip() != ""
                    if getattr(shape, "has_text_frame", False)
                    else False
                )
                # 도형 색상
                fill_color = None
                try:
                    fill = shape.fill
                    if fill.type is not None:
                        try:
                            rgb = fill.fore_color.rgb
                            if rgb is not None:
                                fill_color = str(rgb)
                                fill_color_counter[fill_color] = (
                                    fill_color_counter.get(fill_color, 0) + 1
                                )
                        except Exception:
                            pass
                except Exception:
                    pass

                if not is_text_shape:
                    shape_type = None
                    try:
                        shape_type = (
                            shape.shape_type.name if shape.shape_type else None
                        )
                    except Exception:
                        pass
                    shapes_meta.append(
                        {
                            **pos_info,
                            "fill_color": fill_color,
                            "shape_type": shape_type,
                        }
                    )
                    continue

                # 텍스트 박스
                text = (shape.text_frame.text or "").strip()
                font_size_pt = None
                bold = None
                color_hex = None
                align = None
                try:
                    paras = shape.text_frame.paragraphs
                    if paras:
                        p = paras[0]
                        align = (
                            str(p.alignment).split(".")[-1] if p.alignment else None
                        )
                        runs = p.runs or []
                        f = runs[0].font if runs else p.font
                        if f.size:
                            font_size_pt = float(f.size.pt)
                            font_sizes[font_size_pt] = (
                                font_sizes.get(font_size_pt, 0) + 1
                            )
                        bold = f.bold
                        try:
                            if f.color and f.color.rgb:
                                color_hex = str(f.color.rgb)
                                font_color_counter[color_hex] = (
                                    font_color_counter.get(color_hex, 0) + 1
                                )
                        except Exception:
                            pass
                except Exception:
                    pass

                boxes.append(
                    {
                        "box_id": len(boxes),
                        "original_text": text[:200],
                        "left_emu": int(shape.left or 0),
                        "top_emu": int(shape.top or 0),
                        "width_emu": int(shape.width or 0),
                        "height_emu": int(shape.height or 0),
                        "left_pct": pos_info["left_pct"],
                        "top_pct": pos_info["top_pct"],
                        "width_pct": pos_info["width_pct"],
                        "height_pct": pos_info["height_pct"],
                        "font_size_pt": font_size_pt,
                        "bold": bold,
                        "color_hex": color_hex,
                        "align": align,
                    }
                )

            slides_boxes.append(boxes)
            slides_shapes.append(shapes_meta)

        color_palette = [
            c for c, _ in sorted(
                fill_color_counter.items(), key=lambda x: x[1], reverse=True
            )[:6]
        ]
        font_palette = [
            c for c, _ in sorted(
                font_color_counter.items(), key=lambda x: x[1], reverse=True
            )[:6]
        ]
        top_font_sizes = [
            s for s, _ in sorted(
                font_sizes.items(), key=lambda x: x[1], reverse=True
            )[:5]
        ]

        return {
            "slide_width_emu": sw,
            "slide_height_emu": sh,
            "slides_boxes": slides_boxes,
            "slides_shapes": slides_shapes,
            "color_palette": color_palette,
            "font_palette": font_palette,
            "font_size_palette": top_font_sizes,
        }

    @staticmethod
    def _extract_template_box_specs(template_path: str) -> list[list[dict]]:
        """양식 PPTX 의 각 슬라이드별 텍스트 박스 메타데이터 추출.

        반환: slides[] of boxes[], 각 box 는
        {box_id, original_text, left_emu, top_emu, width_emu, height_emu,
         font_size_pt, bold, color_hex, align}
        """
        from pptx import Presentation
        prs = Presentation(template_path)
        slides_specs: list[list[dict]] = []
        for slide in prs.slides:
            boxes: list[dict] = []
            for shape in slide.shapes:
                if not getattr(shape, "has_text_frame", False):
                    continue
                text = (shape.text_frame.text or "").strip()
                font_size_pt = None
                bold = None
                color_hex = None
                align = None
                try:
                    paras = shape.text_frame.paragraphs
                    if paras:
                        p = paras[0]
                        align = (
                            str(p.alignment).split(".")[-1] if p.alignment else None
                        )
                        runs = p.runs or []
                        f = runs[0].font if runs else p.font
                        if f.size:
                            font_size_pt = float(f.size.pt)
                        bold = f.bold
                        try:
                            if f.color and f.color.rgb:
                                color_hex = str(f.color.rgb)
                        except Exception:
                            pass
                except Exception:
                    pass

                boxes.append(
                    {
                        "box_id": len(boxes),
                        "original_text": text[:200],
                        "left_emu": int(shape.left or 0),
                        "top_emu": int(shape.top or 0),
                        "width_emu": int(shape.width or 0),
                        "height_emu": int(shape.height or 0),
                        "font_size_pt": font_size_pt,
                        "bold": bold,
                        "color_hex": color_hex,
                        "align": align,
                    }
                )
            slides_specs.append(boxes)
        return slides_specs

    @staticmethod
    def _extract_template_slide_texts(template_path: str) -> list[str]:
        """양식 PPTX 의 각 슬라이드 텍스트 추출 (placeholder + textbox 모두)."""
        from pptx import Presentation
        prs = Presentation(template_path)
        texts: list[str] = []
        for slide in prs.slides:
            parts: list[str] = []
            for shape in slide.shapes:
                if not getattr(shape, "has_text_frame", False):
                    continue
                for para in shape.text_frame.paragraphs:
                    line = "".join(run.text for run in para.runs).strip()
                    if line:
                        parts.append(line)
            texts.append("\n".join(parts))
        return texts

    @staticmethod
    def _cosine_distance(a: list[float], b: list[float]) -> float:
        import math
        dot = sum(x * y for x, y in zip(a, b))
        na = math.sqrt(sum(x * x for x in a))
        nb = math.sqrt(sum(y * y for y in b))
        if na == 0 or nb == 0:
            return 1.0
        return 1.0 - dot / (na * nb)

    @staticmethod
    def _find_template_in_sibling_dirs(raw_data_dir: str) -> Optional[str]:
        """raw_data_dir 의 부모 디렉토리에서 '양식'/'template'/'form' 형제 폴더를 찾아
        그 안의 .pptx 파일 경로를 반환. 없으면 None.
        """
        if not raw_data_dir:
            return None
        parent = os.path.dirname(os.path.abspath(raw_data_dir))
        if not os.path.isdir(parent):
            return None
        candidate_names = (
            "양식", "Template", "template", "Templates", "templates",
            "Form", "form", "Forms", "forms", "TEMPLATE", "FORM",
        )
        for name in candidate_names:
            cand_dir = os.path.join(parent, name)
            if not os.path.isdir(cand_dir):
                continue
            for fname in sorted(os.listdir(cand_dir)):
                if fname.startswith(".") or fname.startswith("~$"):
                    continue
                if fname.lower().endswith(".pptx"):
                    return os.path.join(cand_dir, fname)
        return None

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

        # 양식 PPTX 탐색 우선순위
        #  1. raw_data_dir 의 형제 폴더 (양식 / template / form 등) 안의 .pptx
        #  2. DB 의 ingest 된 .pptx (raw_data_dir 외부)
        # 둘 다 실패하면 빈 PPT 생성 (디자인 보존 불가)
        template_path: Optional[str] = self._find_template_in_sibling_dirs(
            request.raw_data_dir
        )
        if template_path:
            logger.info(
                "[GeneratePptx] 양식 템플릿 (파일시스템): %s", template_path
            )
        else:
            db_path = await self._repo.find_template_pptx_path(
                form_type.value,
                exclude_dir=request.raw_data_dir,
            )
            if db_path and os.path.isfile(db_path):
                template_path = db_path
                logger.info(
                    "[GeneratePptx] 양식 템플릿 (DB): %s", template_path
                )
            elif db_path:
                logger.warning(
                    "[GeneratePptx] DB 의 양식 PPTX 경로가 실제 파일이 아님: %s",
                    db_path,
                )

        if not template_path:
            logger.info(
                "[GeneratePptx] 양식 PPTX 를 찾지 못함 (form=%s, raw=%s). "
                "양식 폴더 권장 구조: <raw_data_dir 의 부모>/양식/*.pptx",
                form_type.value, request.raw_data_dir,
            )

        # === 슬라이드 빌드 ===
        slides: list[SlideContent] = []
        total_referenced = 0

        if template_path:
            raw_text_concat = "\n\n".join(
                f"=== {raw.file_name} ===\n{raw.text}" for raw in raw_files
            )

            if self._raw_mapper is not None:
                # === 파싱 + 박스 명세 + 시각 메타 + 시각화 통합 ===
                # 1) 양식 시각 메타 (위치/크기/팔레트)
                visual_meta = self._extract_template_visual_meta(template_path)
                slides_boxes = visual_meta["slides_boxes"]
                slides_shapes = visual_meta["slides_shapes"]

                # 2) 양식 파싱 결과는 ingest 단계(RAG 실행) 에서만 생성한다.
                #    PPT 생성 시점에는 디스크 캐시에서 읽기만 — 없으면 None 으로 진행.
                parsed_template: dict | None = None
                template_cache_key = self._find_template_cache_key(
                    template_path, form_type.value
                )
                if template_cache_key:
                    cached = ParseCache.get(template_cache_key)
                    if cached and "parsed" in cached:
                        parsed_template = cached["parsed"]
                        logger.info(
                            "[GeneratePptx] 양식 파싱 캐시 hit: %s",
                            template_cache_key,
                        )
                if parsed_template is None:
                    logger.info(
                        "[GeneratePptx] 양식 파싱 캐시 miss — ingest 미실행 또는 cache 만료. "
                        "박스 명세만으로 매핑 진행. /api/v1/rag/jobs 로 양식 ingest 하면 다음부터 캐시 활용됨."
                    )

                # 3) raw 파싱
                parsed_raw: dict | None = None
                if self._raw_parser is not None:
                    parsed_raw = await self._raw_parser.parse(raw_text_concat)

                # 4) 매퍼 호출 (파싱된 양식·raw 둘 다 전달)
                llm_outputs = await self._raw_mapper.map_raw_to_box_specs(
                    slides_boxes=slides_boxes,
                    slides_shapes=slides_shapes,
                    color_palette=visual_meta["color_palette"],
                    font_palette=visual_meta["font_palette"],
                    font_size_palette=visual_meta["font_size_palette"],
                    raw_text=raw_text_concat,
                    parsed_template=parsed_template,
                    parsed_raw=parsed_raw,
                )
                used_count = sum(1 for s in llm_outputs if s.get("use"))
                deco_count = sum(
                    len(s.get("decorations", [])) for s in llm_outputs
                )
                logger.info(
                    "[GeneratePptx] LLM 양식 모방+시각화: 양식 %d장 → 사용 %d장, deco %d개",
                    len(slides_boxes), used_count, deco_count,
                )

                os.makedirs(self._output_dir, exist_ok=True)
                result = self._pptx.generate_from_box_specs(
                    form_type=form_type.value,
                    template_path=template_path,
                    slides_specs=slides_boxes,
                    llm_slide_outputs=llm_outputs,
                    output_dir=self._output_dir,
                    slides_background_shapes=slides_shapes,
                )
                file_name = os.path.basename(result.file_path)
                saved_directory = os.path.dirname(result.file_path)
                download_url = f"{self._download_url_prefix}/{file_name}"
                return GeneratePptxResponse(
                    form_type=form_type.value,
                    sheet_name=form_type.value,
                    file_path=result.file_path,
                    saved_directory=saved_directory,
                    file_name=file_name,
                    download_url=download_url,
                    slide_count=result.slide_count,
                    files_read=len(raw_files),
                    chunks_referenced=sum(
                        1 for s in llm_outputs if s.get("use")
                    ),
                )
            else:
                # === LLM 미주입 시 임베딩 기반 폴백 ===
                raw_chunk_pool: list[tuple[str, str]] = []
                for raw in raw_files:
                    for ch in ChunkingService.split(
                        raw.text, chunk_size=400, overlap=0
                    ):
                        raw_chunk_pool.append((raw.file_name, ch))
                if not raw_chunk_pool:
                    raise ValueError(
                        "raw data 파일에서 텍스트 청크를 추출하지 못했습니다."
                    )
                raw_embeddings = await self._embedding.generate_batch(
                    [c[1] for c in raw_chunk_pool]
                )
                non_empty_indices = [
                    i for i, t in enumerate(template_slide_texts) if t.strip()
                ]
                slide_emb_map: dict[int, list[float]] = {}
                if non_empty_indices:
                    slide_embs = await self._embedding.generate_batch(
                        [template_slide_texts[i] for i in non_empty_indices]
                    )
                    slide_emb_map = dict(zip(non_empty_indices, slide_embs))
                fallback_layout_idx = (
                    non_empty_indices[0] if non_empty_indices else 0
                )
                for (file_name, chunk_text), chunk_emb in zip(
                    raw_chunk_pool, raw_embeddings
                ):
                    best_idx = fallback_layout_idx
                    best_dist = 2.0
                    for slide_idx, slide_emb in slide_emb_map.items():
                        d = self._cosine_distance(chunk_emb, slide_emb)
                        if d < best_dist:
                            best_dist = d
                            best_idx = slide_idx
                    slides.append(
                        SlideContent(
                            title=file_name[:80],
                            body=chunk_text,
                            source_slide_index=best_idx,
                        )
                    )
                    total_referenced += 1
                logger.info(
                    "[GeneratePptx] 임베딩 폴백 매칭 (LLM 미주입): raw 청크 %d개 → 결과 %d장",
                    len(raw_chunk_pool), len(slides),
                )
        else:
            # 빈 PPT 모드: raw 파일별로 슬라이드 1개씩
            for raw in raw_files:
                raw_chunks = ChunkingService.split(
                    raw.text, chunk_size=800, overlap=0
                )
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
            template_path=template_path,
        )

        file_name = os.path.basename(result.file_path)
        saved_directory = os.path.dirname(result.file_path)
        download_url = f"{self._download_url_prefix}/{file_name}"

        return GeneratePptxResponse(
            form_type=form_type.value,
            sheet_name=form_type.value,
            file_path=result.file_path,
            saved_directory=saved_directory,
            file_name=file_name,
            download_url=download_url,
            slide_count=result.slide_count,
            files_read=len(raw_files),
            chunks_referenced=total_referenced,
        )
