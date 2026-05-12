from typing import Optional

from pydantic import BaseModel


class IdentifyTemplateResponse(BaseModel):
    form_type: str
    sheet: str
    identified: Optional[str] = None   # raw data 기반 자동 식별된 form_type
    identified_distance: Optional[float] = None  # 작을수록 유사
    exists: bool                # 양식 sheet 에 청크가 등록되어 있는지
    chunk_count: int            # 등록된 청크 수
    raw_data_folder: Optional[str] = None
    raw_data_supported_files: Optional[int] = None
    ready: bool                 # PPT 생성 가능 여부 (template 존재 + raw data 폴더 사용 가능)
    message: str
