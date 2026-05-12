from typing import Optional

from pydantic import AliasChoices, BaseModel, ConfigDict, Field


class CreateRagJobRequest(BaseModel):
    """프론트가 양식 / 폴더 / 시트 한 쌍을 보내 RAG ingest 작업을 만든다."""

    model_config = ConfigDict(populate_by_name=True)

    form_type: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("form_type", "formType", "form", "type"),
        description="양식 종류 (FRS, Strategy, IssueHistory, FrameStatus, WeakpointMonitoringStatus, LayerFrameMargin)",
    )
    folder: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices(
            "folder", "folder_path", "folderPath", "path"
        ),
        description="해당 양식 파일들이 들어있는 절대 경로",
    )
    sheet: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("sheet", "sheet_name", "sheetName"),
        description="저장 sheet 이름 (생략 시 form_type 사용)",
    )
