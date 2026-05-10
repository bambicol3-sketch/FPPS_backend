"""멀티 에이전트 그래프 스모크 실행 스크립트.

직접 실행:
    python -m app.infrastructure.multi_agent.smoke "안녕"

기본값은 "안녕" 입력으로 그래프를 1회 실행한다.
"""
import asyncio
import logging
import sys

from app.infrastructure.config.logging_config import setup_logging
from app.infrastructure.multi_agent.exceptions import MultiAgentError
from app.infrastructure.multi_agent.runner import MultiAgentInput, run_multi_agent

logger = logging.getLogger(__name__)


async def main(query: str) -> int:
    setup_logging()
    logger.info("[smoke] 시작 query=%r", query)
    try:
        result = await run_multi_agent(MultiAgentInput(query=query))
    except MultiAgentError as exc:
        logger.error("[smoke] 실패: %s", exc)
        return 1

    print("=" * 60)
    print(f"[query] {query}")
    print(f"[plan]\n{result.plan}")
    print(f"[research]\n{result.research}")
    print(f"[analysis]\n{result.analysis}")
    print(f"[review]\n{result.review}")
    print(f"[final_answer]\n{result.final_answer}")
    print(f"[steps] {result.step_count}")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    q = sys.argv[1] if len(sys.argv) > 1 else "안녕"
    sys.exit(asyncio.run(main(q)))
