from __future__ import annotations

from pydantic import BaseModel

from app.domains.semiconductor.domain.entity.semiconductor_analysis import (
    ConversationStep,
    SemiconductorAnalysis,
)


class ConversationStepResponse(BaseModel):
    role: str
    node: str
    content: str


class SemiconductorAnalysisResponse(BaseModel):
    ticker: str
    company_name: str
    segment: str
    query: str
    final_answer: str
    plan: str
    research: str
    analysis: str
    conversation: list[ConversationStepResponse]
    step_count: int

    @classmethod
    def from_entity(cls, entity: SemiconductorAnalysis) -> "SemiconductorAnalysisResponse":
        return cls(
            ticker=entity.ticker,
            company_name=entity.company_name,
            segment=entity.segment,
            query=entity.query,
            final_answer=entity.final_answer,
            plan=entity.plan,
            research=entity.research,
            analysis=entity.analysis,
            conversation=[
                ConversationStepResponse(
                    role=step.role,
                    node=step.node,
                    content=step.content,
                )
                for step in entity.conversation
            ],
            step_count=entity.step_count,
        )


class SemiconductorCompanyResponse(BaseModel):
    ticker: str
    company_name: str
    segment: str
