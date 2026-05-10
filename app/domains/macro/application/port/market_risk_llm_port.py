from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List


@dataclass
class LlmRiskResult:
    stance: str
    reasons: List[str]
    raw_text: str


class MarketRiskLlmPort(ABC):
    """오늘 기준 시장 Risk-on/Risk-off 판단을 LLM에 질의하는 포트."""

    @abstractmethod
    async def ask(self, system_instructions: str, user_prompt: str) -> LlmRiskResult:
        raise NotImplementedError
