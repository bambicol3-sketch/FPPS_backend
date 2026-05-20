import uuid
from dataclasses import dataclass
from typing import Optional

from app.domains.template_rag.application.port.chat_llm_port import ChatLlmPort
from app.domains.template_rag.application.port.chat_session_store_port import (
    ChatSessionStorePort,
)
from app.domains.template_rag.application.request.generate_pptx_request import (
    GeneratePptxRequest,
)
from app.domains.template_rag.application.usecase.generate_pptx_from_template_usecase import (
    GeneratePptxFromTemplateUseCase,
)
from app.domains.template_rag.domain.entity.chat_session import ChatSession
from app.domains.template_rag.domain.value_object.form_type import FormType

_SYSTEM_PROMPT = """당신은 PPT 생성 도우미입니다. 사용자가 원하는 PPT를 만들 수 있도록 안내합니다.

PPT 생성에 필요한 두 가지 정보:
1. form_type (양식 종류): FRS, Strategy, IssueHistory, FrameStatus, WeakpointMonitoringStatus, LayerFrameMargin
2. raw_data_dir: raw data 파일들이 있는 폴더의 절대 경로 (예: /Users/username/projects/my_data)

두 정보가 모두 확인되면 generate_pptx 함수를 호출하세요.
정보가 부족하면 친절하게 한 가지씩 질문하세요.
경로는 절대 경로 형식인지 확인하고, 불분명하면 다시 물어보세요.
항상 한국어로 짧고 명확하게 응답하세요."""


@dataclass
class ChatPptxResult:
    session_id: str
    reply: str
    status: str  # "active" | "done"
    result: Optional[dict] = None


class ChatPptxUseCase:
    def __init__(
        self,
        session_store: ChatSessionStorePort,
        chat_llm: ChatLlmPort,
        generate_pptx_usecase: GeneratePptxFromTemplateUseCase,
    ) -> None:
        self._store = session_store
        self._llm = chat_llm
        self._gen = generate_pptx_usecase

    async def execute(self, message: str, session_id: Optional[str]) -> ChatPptxResult:
        sid = session_id or str(uuid.uuid4())
        session = self._store.load(sid) or ChatSession(session_id=sid)

        if session.status == "done":
            return ChatPptxResult(
                session_id=sid,
                reply="이미 PPT 생성이 완료된 세션입니다. 새 대화를 시작하려면 session_id 없이 요청하세요.",
                status="done",
                result=session.result,
            )

        session.add_message("user", message)

        llm_resp = await self._llm.chat(session.messages, _SYSTEM_PROMPT)

        if llm_resp.tool_call and llm_resp.tool_call.name == "generate_pptx":
            args = llm_resp.tool_call.arguments
            try:
                form_type_obj = FormType.from_string(args.get("form_type", ""))
                gen_req = GeneratePptxRequest(
                    form_type=form_type_obj.value,
                    raw_data_dir=args.get("raw_data_dir", ""),
                    top_k=5,
                )
                pptx_result = await self._gen.execute(gen_req)

                reply = (
                    f"PPT 생성이 완료되었습니다!\n"
                    f"파일명: {pptx_result.file_name}\n"
                    f"슬라이드: {pptx_result.slide_count}장\n"
                    f"다운로드: {pptx_result.download_url}"
                )
                result_dict = {
                    "file_name": pptx_result.file_name,
                    "file_path": pptx_result.file_path,
                    "download_url": pptx_result.download_url,
                    "slide_count": pptx_result.slide_count,
                    "files_read": pptx_result.files_read,
                }
                session.status = "done"
                session.result = result_dict
            except Exception as e:
                reply = f"PPT 생성 중 오류가 발생했습니다: {e}\n경로나 양식 종류를 확인 후 다시 알려주세요."
                result_dict = None
        else:
            reply = llm_resp.content or "죄송합니다, 응답을 생성하지 못했습니다."
            result_dict = None

        session.add_message("assistant", reply)
        self._store.save(session)

        return ChatPptxResult(
            session_id=sid,
            reply=reply,
            status=session.status,
            result=result_dict,
        )
