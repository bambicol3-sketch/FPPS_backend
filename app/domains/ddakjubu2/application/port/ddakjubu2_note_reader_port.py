from abc import ABC, abstractmethod
from typing import List

from app.domains.ddakjubu2.domain.entity.learning_note import LearningNote


class Ddakjubu2NoteReaderPort(ABC):
    """기존 Markdown 학습 노트 파일에서 LearningNote 를 읽어오는 포트 (백필용)."""

    @abstractmethod
    def read_notes(self) -> List[LearningNote]:
        raise NotImplementedError

    @abstractmethod
    def source_path(self) -> str:
        raise NotImplementedError
