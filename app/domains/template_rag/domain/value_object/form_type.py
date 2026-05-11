from enum import Enum


class FormType(str, Enum):
    FRS = "FRS"
    STRATEGY = "Strategy"
    ISSUE_HISTORY = "IssueHistory"
    FRAME_STATUS = "FrameStatus"
    WEAKPOINT_MONITORING_STATUS = "WeakpointMonitoringStatus"
    LAYER_FRAME_MARGIN = "LayerFrameMargin"

    @classmethod
    def from_string(cls, value: str) -> "FormType":
        normalized = (
            value.strip().lower().replace(" ", "").replace("_", "").replace("별", "")
        )
        aliases = {
            "frs": cls.FRS,
            "strategy": cls.STRATEGY,
            "issuehistory": cls.ISSUE_HISTORY,
            "framestatus": cls.FRAME_STATUS,
            "weakpointmonitoringstatus": cls.WEAKPOINT_MONITORING_STATUS,
            "layerframemargin": cls.LAYER_FRAME_MARGIN,
        }
        if normalized not in aliases:
            supported = ", ".join(ft.value for ft in cls)
            raise ValueError(
                f"지원하지 않는 양식 종류입니다: {value!r}. 지원: {supported}"
            )
        return aliases[normalized]

    @property
    def sheet_name(self) -> str:
        return self.value
