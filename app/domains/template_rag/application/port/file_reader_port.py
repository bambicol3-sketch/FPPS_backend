from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class ExtractedFile:
    file_path: str
    file_name: str
    text: str
    file_hash: str


class FileReaderPort(ABC):
    @abstractmethod
    def collect(self, folder_path: str) -> list[ExtractedFile]:
        """폴더에서 지원 확장자 파일을 재귀 수집하고 텍스트를 추출한다."""
