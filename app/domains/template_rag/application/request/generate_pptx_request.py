from pydantic import BaseModel, Field


class GeneratePptxRequest(BaseModel):
    form_type: str = Field(description="양식 sheet (FRS, Strategy, IssueHistory, FrameStatus, WeakpointMonitoringStatus, LayerFrameMargin)")
    raw_data_dir: str = Field(description="raw data 폴더 경로")
    top_k: int = Field(default=5, ge=1, le=20)
