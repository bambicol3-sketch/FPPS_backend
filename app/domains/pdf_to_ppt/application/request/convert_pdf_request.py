from dataclasses import dataclass


@dataclass
class ConvertPdfRequest:
    file_bytes: bytes
    file_name: str
