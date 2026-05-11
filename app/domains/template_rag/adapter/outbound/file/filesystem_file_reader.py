import hashlib
import logging
import os
from pathlib import Path

from app.domains.template_rag.application.port.file_reader_port import (
    ExtractedFile,
    FileReaderPort,
)

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {".txt", ".md", ".pdf", ".docx", ".pptx"}


class FilesystemFileReader(FileReaderPort):
    def collect(self, folder_path: str) -> list[ExtractedFile]:
        if not folder_path or not os.path.isdir(folder_path):
            return []

        extracted: list[ExtractedFile] = []
        for path in sorted(Path(folder_path).rglob("*")):
            if not path.is_file():
                continue
            ext = path.suffix.lower()
            if ext not in SUPPORTED_EXTENSIONS:
                continue
            try:
                text = self._extract_text(path, ext)
                if not text.strip():
                    continue
                file_bytes = path.read_bytes()
                file_hash = hashlib.sha256(file_bytes).hexdigest()
                extracted.append(
                    ExtractedFile(
                        file_path=str(path.resolve()),
                        file_name=path.name,
                        text=text,
                        file_hash=file_hash,
                    )
                )
            except Exception as e:
                logger.warning("[FileReader] %s 추출 실패: %s", path, e)
        return extracted

    def _extract_text(self, path: Path, ext: str) -> str:
        if ext in {".txt", ".md"}:
            return path.read_text(encoding="utf-8", errors="ignore")
        if ext == ".pdf":
            return self._extract_pdf(path)
        if ext == ".docx":
            return self._extract_docx(path)
        if ext == ".pptx":
            return self._extract_pptx(path)
        return ""

    @staticmethod
    def _extract_pdf(path: Path) -> str:
        try:
            from pypdf import PdfReader
        except ImportError as e:
            raise RuntimeError(
                "pypdf 가 설치되어 있지 않습니다. pip install pypdf"
            ) from e
        reader = PdfReader(str(path))
        return "\n\n".join((p.extract_text() or "") for p in reader.pages)

    @staticmethod
    def _extract_docx(path: Path) -> str:
        try:
            import docx
        except ImportError as e:
            raise RuntimeError(
                "python-docx 가 설치되어 있지 않습니다. pip install python-docx"
            ) from e
        document = docx.Document(str(path))
        return "\n".join(p.text for p in document.paragraphs if p.text)

    @staticmethod
    def _extract_pptx(path: Path) -> str:
        try:
            from pptx import Presentation
        except ImportError as e:
            raise RuntimeError(
                "python-pptx 가 설치되어 있지 않습니다. pip install python-pptx"
            ) from e
        prs = Presentation(str(path))
        parts: list[str] = []
        for slide in prs.slides:
            for shape in slide.shapes:
                if not getattr(shape, "has_text_frame", False):
                    continue
                for para in shape.text_frame.paragraphs:
                    line = "".join(run.text for run in para.runs)
                    if line.strip():
                        parts.append(line)
        return "\n".join(parts)
