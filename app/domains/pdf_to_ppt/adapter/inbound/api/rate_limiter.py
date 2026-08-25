import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request

# 인증 없는 퍼블릭 엔드포인트라 IP 기준 in-memory rate limit 으로 어뷰징을 최소 방어한다.
# 서버 재시작 시 초기화되며, 멀티 프로세스/인스턴스 배포에는 적용되지 않는다 (추후 Redis 전환 고려).
_WINDOW_SECONDS = 60
_MAX_REQUESTS_PER_WINDOW = 5

_hits: dict[str, deque] = defaultdict(deque)


def enforce_rate_limit(request: Request) -> None:
    client_ip = request.client.host if request.client else "unknown"
    now = time.monotonic()
    window = _hits[client_ip]

    while window and now - window[0] > _WINDOW_SECONDS:
        window.popleft()

    if len(window) >= _MAX_REQUESTS_PER_WINDOW:
        raise HTTPException(
            status_code=429,
            detail="요청이 너무 많습니다. 잠시 후 다시 시도해주세요.",
        )
    window.append(now)
