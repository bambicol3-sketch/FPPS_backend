from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ConversationStep:
    role: str
    node: str
    content: str


@dataclass
class SemiconductorAnalysis:
    ticker: str
    company_name: str
    segment: str
    query: str
    final_answer: str
    plan: str
    research: str
    analysis: str
    review: str
    conversation: list[ConversationStep] = field(default_factory=list)
    step_count: int = 0
