import logging

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, Request

from app.common.exception.app_exception import AppException
from app.common.response.base_response import BaseResponse
from app.domains.semiconductor.adapter.outbound.external.semiconductor_analysis_adapter import (
    SemiconductorAnalysisAdapter,
)
from app.domains.semiconductor.application.request.semiconductor_analysis_request import (
    SemiconductorAnalysisRequest,
)
from app.domains.semiconductor.application.response.semiconductor_analysis_response import (
    SemiconductorAnalysisResponse,
    SemiconductorCompanyResponse,
)
from app.domains.semiconductor.application.usecase.analyze_semiconductor_usecase import (
    AnalyzeSemiconductorUseCase,
)
from app.domains.semiconductor.domain.value_object.semiconductor_company import SemiconductorCompany
from app.infrastructure.cache.redis_client import get_redis

logger = logging.getLogger(__name__)

SESSION_KEY_PREFIX = "session:"

router = APIRouter(prefix="/semiconductor", tags=["Semiconductor"])


async def _require_auth(request: Request, redis: aioredis.Redis) -> None:
    auth_header = request.headers.get("authorization", "")
    bearer_token = auth_header.removeprefix("Bearer ").strip() if auth_header else ""
    token = (
        request.query_params.get("token")
        or request.cookies.get("user_token")
        or request.cookies.get("temp_token")
        or (bearer_token or None)
        or request.headers.get("x-auth-token")
    )
    if not token:
        raise AppException(status_code=401, message="인증이 필요합니다.")
    if not await redis.get(f"{SESSION_KEY_PREFIX}{token}"):
        raise AppException(status_code=401, message="세션이 만료되었거나 유효하지 않습니다.")


@router.get(
    "/companies",
    response_model=BaseResponse[list[SemiconductorCompanyResponse]],
    summary="반도체 주요 종목 목록",
)
async def list_companies():
    """네비게이션바에 표시할 국내 반도체 주요 종목 목록을 반환합니다."""
    companies = [
        SemiconductorCompanyResponse(
            ticker=c.ticker,
            company_name=c.name,
            segment=c.segment,
        )
        for c in SemiconductorCompany.kr_companies()
    ]
    return BaseResponse.ok(data=companies)


@router.post(
    "/analyze",
    response_model=BaseResponse[SemiconductorAnalysisResponse],
    summary="반도체 데이터 분석",
)
async def analyze_semiconductor(
    body: SemiconductorAnalysisRequest,
    request: Request,
    redis: aioredis.Redis = Depends(get_redis),
):
    """멀티 에이전트를 통해 반도체 기업 분석을 수행하고 백그라운드 대화 과정을 함께 반환합니다."""
    await _require_auth(request, redis)

    usecase = AnalyzeSemiconductorUseCase(
        analysis_port=SemiconductorAnalysisAdapter(),
    )
    result = await usecase.execute(body)
    return BaseResponse.ok(data=SemiconductorAnalysisResponse.from_entity(result))
