from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import List


class RiskStance(str, Enum):
    RISK_ON = "Risk-on"
    RISK_OFF = "Risk-off"
    NEUTRAL = "Neutral"
    UNKNOWN = "Unknown"


@dataclass
class MarketRiskAssessment:
    as_of: date
    stance: RiskStance
    reason_lines: List[str] = field(default_factory=list)
    referenced_video_ids: List[str] = field(default_factory=list)
    note: str = ""

    def reason_summary(self) -> str:
        return "\n".join(self.reason_lines[:5])
