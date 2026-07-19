import re
import time
import uuid
from typing import List, Optional

from app.domains.fab_agent.application.port.fab_document_repository_port import (
    FabDocumentRepositoryPort,
)
from app.domains.fab_agent.application.port.fab_llm_ports import (
    FabEmbeddingPort,
    FabLlmPort,
)
from app.domains.fab_agent.application.port.fab_persistence_ports import (
    FabAuditRepositoryPort,
    FabChatRepositoryPort,
)
from app.domains.fab_agent.domain.entity.fab_user_access import FabUserAccess
from app.domains.fab_agent.application.response.fab_responses import (
    AskResponse,
    FabCitationDto,
)
from app.domains.fab_agent.domain.entity.fab_answer import RetrievedChunk
from app.domains.fab_agent.domain.service.knowledge_prompt_builder import (
    KnowledgePromptBuilder,
)

CITATION_PATTERN = re.compile(r"\[(\d{1,2})\]")
REFUSAL_TEXT = "근거 문서를 찾지 못했습니다"


class AskKnowledgeUseCase:
    """권한 인지 검색 → 근거 검증 → LLM 답변 → 불변 감사 로깅.

    가드레일: 검색 결과 0건이면 LLM 을 호출하지 않고 답변을 거부한다 (환각 방지).
    """

    def __init__(
        self,
        document_repository_port: FabDocumentRepositoryPort,
        embedding_port: FabEmbeddingPort,
        llm_port: FabLlmPort,
        audit_repository_port: FabAuditRepositoryPort,
        chat_repository_port: FabChatRepositoryPort,
        top_k: int = 6,
        max_history_turns: int = 6,
    ):
        self._document_repository_port = document_repository_port
        self._embedding_port = embedding_port
        self._llm_port = llm_port
        self._audit_repository_port = audit_repository_port
        self._chat_repository_port = chat_repository_port
        self._top_k = top_k
        self._max_history_turns = max_history_turns
        self._prompt_builder = KnowledgePromptBuilder()

    async def execute(
        self, access: FabUserAccess, question: str, session_id: Optional[str]
    ) -> AskResponse:
        started = time.monotonic()
        account_email = access.account_email
        session_id = session_id or uuid.uuid4().hex
        request_id = uuid.uuid4().hex

        history = await self._chat_repository_port.recent_messages(
            session_id, limit=self._max_history_turns
        )

        try:
            query_embedding = await self._embedding_port.embed(question)
        except Exception as e:
            print(f"[fab_agent] 질문 임베딩 실패(키워드 검색만 사용) error={e}", flush=True)
            query_embedding = None

        chunks = await self._document_repository_port.search_chunks(
            query_embedding=query_embedding,
            keyword=question,
            clearance_grade=access.clearance_grade,
            modules=access.modules,
            top_k=self._top_k,
        )

        if not chunks:
            answer_text = (
                f"{REFUSAL_TEXT}. 접근 가능한 문서 범위(등급 {access.clearance_grade} 이하, "
                f"모듈 {', '.join(access.modules) or 'COMMON'}) 안에서 관련 근거가 없어 "
                "답변을 드릴 수 없습니다."
            )
            response = AskResponse(
                request_id=request_id,
                session_id=session_id,
                answer=answer_text,
                citations=[],
                used_grade_max=0,
                refused=True,
                refusal_reason="근거 문서 없음",
            )
            await self._persist(
                account_email, session_id, question, response, started
            )
            return response

        prompt = self._prompt_builder.build(question, chunks, history)
        raw_answer = await self._llm_port.answer(
            KnowledgePromptBuilder.SYSTEM_INSTRUCTIONS, prompt
        )

        citations = self._extract_citations(raw_answer, chunks)
        refused = REFUSAL_TEXT in raw_answer and not citations
        used_grade_max = max((c.security_grade for c in citations), default=0)
        if not refused and not citations:
            # 인용 없는 답변은 근거 미확인 → 사용 청크 최대 등급으로 보수적 표기
            used_grade_max = max(c.security_grade for c in chunks)

        response = AskResponse(
            request_id=request_id,
            session_id=session_id,
            answer=raw_answer.strip(),
            citations=citations,
            used_grade_max=used_grade_max,
            refused=refused,
            refusal_reason="근거 문서 없음" if refused else "",
        )
        await self._persist(account_email, session_id, question, response, started)
        return response

    async def _persist(
        self,
        account_email: str,
        session_id: str,
        question: str,
        response: AskResponse,
        started: float,
    ) -> None:
        latency_ms = int((time.monotonic() - started) * 1000)
        citations_json = [c.model_dump() for c in response.citations]
        try:
            await self._audit_repository_port.save(
                request_id=response.request_id,
                account_email=account_email,
                session_id=session_id,
                question=question,
                answer=response.answer,
                citations=citations_json,
                used_grade_max=response.used_grade_max,
                refused=response.refused,
                latency_ms=latency_ms,
            )
        except Exception as e:
            print(f"[fab_agent] 감사 로그 저장 실패: {e}", flush=True)
        try:
            await self._chat_repository_port.save_message(
                session_id, account_email, "user", question
            )
            await self._chat_repository_port.save_message(
                session_id,
                account_email,
                "assistant",
                response.answer,
                citations=citations_json,
            )
        except Exception as e:
            print(f"[fab_agent] 대화 이력 저장 실패: {e}", flush=True)

    @staticmethod
    def _extract_citations(
        answer: str, chunks: List[RetrievedChunk]
    ) -> List[FabCitationDto]:
        cited_numbers = sorted(
            {
                int(m)
                for m in CITATION_PATTERN.findall(answer)
                if 1 <= int(m) <= len(chunks)
            }
        )
        citations: List[FabCitationDto] = []
        for n in cited_numbers:
            chunk = chunks[n - 1]
            quote = chunk.text[:200] + ("…" if len(chunk.text) > 200 else "")
            citations.append(
                FabCitationDto(
                    ref_number=n,
                    doc_id=chunk.doc_id,
                    title=chunk.title,
                    chunk_index=chunk.chunk_index,
                    quote=quote,
                    security_grade=chunk.security_grade,
                    owner_module=chunk.owner_module,
                )
            )
        return citations
