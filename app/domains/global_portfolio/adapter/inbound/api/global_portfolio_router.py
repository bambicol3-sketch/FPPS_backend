from typing import Literal

from fastapi import APIRouter, Query

from app.common.response.base_response import BaseResponse
from app.domains.global_portfolio.application.response.nps_holdings_response import (
    NpsHoldingsResponse,
)
from app.domains.global_portfolio.application.usecase.get_nps_holdings_usecase import (
    GetNpsHoldingsUseCase,
)

router = APIRouter(prefix="/global-portfolio", tags=["Global Portfolio"])


@router.get(
    "/nps-holdings",
    response_model=BaseResponse[NpsHoldingsResponse],
    summary="국민연금공단 주요 보유종목",
)
async def get_nps_holdings(
    market: Literal["all", "domestic", "overseas"] = Query(
        default="all",
        description="조회 시장 구분: all(전체) | domestic(국내) | overseas(해외)",
    ),
):
    """국민연금공단(NPS)의 국내·해외 주요 보유종목 목록을 반환합니다.

    - **domestic**: 국내 KRX 상장 종목
    - **overseas**: 해외 상장 종목 (미국 NYSE/NASDAQ 중심)
    - **all**: 전체 (기본값)

    데이터 출처: NPS 분기별 포트폴리오 공시 및 DART 5% 지분 공시 (2024~2025 기준)
    """
    usecase = GetNpsHoldingsUseCase()
    result = await usecase.execute(market)
    return BaseResponse.ok(data=result)
