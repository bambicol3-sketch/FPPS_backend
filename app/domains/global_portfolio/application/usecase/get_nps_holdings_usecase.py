from __future__ import annotations

from typing import Literal

from app.domains.global_portfolio.adapter.outbound.external.nps_holdings_provider import (
    get_nps_holdings,
)
from app.domains.global_portfolio.application.response.nps_holdings_response import (
    NpsHoldingItem,
    NpsHoldingsResponse,
)


class GetNpsHoldingsUseCase:
    async def execute(
        self, market: Literal["all", "domestic", "overseas"] = "all"
    ) -> NpsHoldingsResponse:
        if market == "all":
            domestic = get_nps_holdings("domestic")
            overseas = get_nps_holdings("overseas")
        elif market == "domestic":
            domestic = get_nps_holdings("domestic")
            overseas = []
        else:
            domestic = []
            overseas = get_nps_holdings("overseas")

        return NpsHoldingsResponse(
            domestic=[NpsHoldingItem.from_entity(h) for h in domestic],
            overseas=[NpsHoldingItem.from_entity(h) for h in overseas],
            total_count=len(domestic) + len(overseas),
        )
