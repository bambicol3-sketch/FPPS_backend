from abc import ABC, abstractmethod


class DdakjubuFileReaderPort(ABC):
    """ddakjubu.md 파일 내용을 컨텍스트로 읽어오는 포트."""

    @abstractmethod
    def read_content(self) -> str:
        """파일이 없거나 비어있으면 빈 문자열을 반환한다."""
        raise NotImplementedError
