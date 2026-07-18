from abc import ABC, abstractmethod


class StockContextProviderPort(ABC):
    """방법론 적용 대상 종목의 데이터 컨텍스트(텍스트 블록)를 조립하는 포트.

    데이터 소스 일부가 실패해도 예외를 내지 않고, 컨텍스트에 '제공되지 않음' 으로
    명시해 LLM 이 missing_data 로 처리하게 한다.
    """

    @abstractmethod
    async def build_context(
        self, ticker: str, stock_name: str, market: str
    ) -> str:
        raise NotImplementedError
