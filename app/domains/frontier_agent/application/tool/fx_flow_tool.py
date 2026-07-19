from datetime import datetime, timezone
from typing import List, Optional

from app.domains.frontier_agent.application.port.frontier_ports import FrontierToolPort
from app.domains.frontier_agent.domain.entity.analysis_run import ToolEvidence

# 딱주부 슬라이드의 외환/수급 데이터 원천 목록 (현재 코드베이스 미연결)
FX_SOURCES = [
    ("CFTC", "미국 연방 규제기관 — 트레이더 신고 내역", "자체 집계", "주 1회(금요일)"),
    ("CME", "미국 파생상품 거래소 — 통화선물·옵션", "거래소 청산·결제", "일별 가격·OI"),
    ("예탁결제원", "스왑·NDF 거래정보 저장소", "수신·공개", "실시간·누적"),
    ("KRX", "원달러 선물 투자자별 거래", "KRX 집계·검증", "영업일 기준"),
    ("한국은행", "통화정책 결정문·참고자료", "한국은행 내부", "금통위 당일"),
]


class FxFlowTool(FrontierToolPort):
    """외환·수급 데이터(CFTC/CME/예탁결제원/KRX/한국은행) 도구.

    이 데이터 소스들은 아직 코드베이스에 연결되지 않았다. 도구는 '미연결'을 provenance 로
    정직하게 반환하고, Analyst 가 이를 missing_data 로 처리하게 한다. (P3에서 pykrx 수급 등 실연결)
    """

    name = "fx_flow"
    description = "외환·투자자별 수급 데이터(CFTC/CME/예탁결제원/KRX/한국은행) — 현재 미연결"

    def applies(self, question: str, ticker: Optional[str]) -> bool:
        keywords = ("환율", "달러", "외환", "수급", "외국인", "선물", "fx", "환")
        return any(k in question.lower() for k in keywords)

    async def gather(
        self, question: str, ticker: Optional[str], stock_name: Optional[str]
    ) -> List[ToolEvidence]:
        catalog = "; ".join(f"{name}({origin})" for name, origin, _, _ in FX_SOURCES)
        return [
            ToolEvidence(
                tool=self.name,
                source_institution="외환·수급 다기관(CFTC/CME/예탁결제원/KRX/한국은행)",
                data_origin="기관별 상이 — 각 자료가 태어나는 곳이 다름",
                collected_by="기관별 상이",
                publish_method="주간/일별/실시간 혼재",
                content=(
                    "외환·수급 데이터 소스가 아직 연결되지 않았습니다. "
                    f"연결 예정 원천: {catalog}. "
                    "현재는 이 축의 정량 판단을 보류해야 합니다."
                ),
                available=False,
                retrieved_at=datetime.now(timezone.utc),
            )
        ]
