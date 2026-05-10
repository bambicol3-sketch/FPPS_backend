from typing import Optional

import redis.asyncio as aioredis
from fastapi import APIRouter, Cookie, Depends

from app.common.exception.app_exception import AppException
from app.common.response.base_response import BaseResponse
from app.domains.investment.adapter.outbound.workflow.langgraph_agent_workflow_adapter import (
    LangGraphAgentWorkflowAdapter,
)
from app.domains.investment.application.request.investment_decision_request import (
    InvestmentDecisionRequest,
)
from app.domains.investment.application.response.investment_decision_response import (
    InvestmentDecisionResponse,
)
from app.domains.investment.application.usecase.make_investment_decision_usecase import (
    MakeInvestmentDecisionUseCase,
)
from app.infrastructure.cache.redis_client import get_redis

SESSION_KEY_PREFIX = "session:"

router = APIRouter(prefix="/investment", tags=["Investment"])


@router.post(
    "/decision",
    response_model=BaseResponse[InvestmentDecisionResponse],
    status_code=200,
)
async def request_investment_decision(
    request: InvestmentDecisionRequest,
    user_token: Optional[str] = Cookie(default=None),
    redis: aioredis.Redis = Depends(get_redis),
):
    """인증된 사용자의 투자 판단 질의를 멀티 에이전트 워크플로우로 처리한다.

    - 인증: Cookie `user_token`
    - 입력: 투자 관련 질의 텍스트
    - 응답: Retrieval → Analysis → Synthesis 단계로 합성된 참고 응답
    """
    if not user_token:
        raise AppException(status_code=401, message="인증이 필요합니다.")

    account_id_raw = await redis.get(f"{SESSION_KEY_PREFIX}{user_token}")
    if not account_id_raw:
        raise AppException(status_code=401, message="세션이 만료되었거나 유효하지 않습니다.")
    account_id = int(account_id_raw)

    usecase = MakeInvestmentDecisionUseCase(
        workflow_port=LangGraphAgentWorkflowAdapter(),
    )
    result = await usecase.execute(account_id=account_id, request=request)
    return BaseResponse.ok(data=result)
