from typing import Optional

import redis.asyncio as aioredis
from fastapi import Cookie, Depends, Header
from sqlalchemy import select

from app.common.exception.app_exception import AppException
from app.domains.account.infrastructure.orm.account_orm import AccountOrm
from app.domains.fab_agent.adapter.outbound.persistence.fab_persistence_impls import (
    FabAccessRepositoryImpl,
)
from app.domains.fab_agent.domain.entity.fab_user_access import FabUserAccess
from app.infrastructure.cache.redis_client import get_redis
from app.infrastructure.config.settings import get_settings
from app.infrastructure.database.database import AsyncSessionLocal

SESSION_KEY_PREFIX = "session:"


async def resolve_user_email(
    user_token: Optional[str] = Cookie(default=None),
    authorization: Optional[str] = Header(default=None),
    x_fab_user: Optional[str] = Header(default=None),
    redis: aioredis.Redis = Depends(get_redis),
) -> str:
    """세션 토큰(쿠키 또는 Bearer) → Redis 세션 → account email.

    개발 환경 한정(fab_auth_dev_header=True)으로 X-Fab-User 헤더 대체를 허용한다.
    """
    settings = get_settings()

    token = user_token
    if not token and authorization and authorization.startswith("Bearer "):
        token = authorization.removeprefix("Bearer ").strip()

    if token:
        account_id_str = await redis.get(f"{SESSION_KEY_PREFIX}{token}")
        if account_id_str:
            async with AsyncSessionLocal() as session:
                row = (
                    await session.execute(
                        select(AccountOrm).where(
                            AccountOrm.id == int(account_id_str)
                        )
                    )
                ).scalar_one_or_none()
            if row is not None and row.email:
                return row.email.strip().lower()

    if settings.fab_auth_dev_header and x_fab_user:
        return x_fab_user.strip().lower()

    raise AppException(status_code=401, message="로그인이 필요합니다.")


async def resolve_access(email: str) -> FabUserAccess:
    """이메일 → 접근 권한. 설정된 관리자 이메일은 최초 접근 시 자동 부트스트랩."""
    settings = get_settings()
    repository = FabAccessRepositoryImpl()

    access = await repository.get_access(email)
    if access is not None:
        return access

    admin_emails = {
        e.strip().lower()
        for e in settings.fab_admin_emails.split(",")
        if e.strip()
    }
    if email in admin_emails:
        access = FabUserAccess(
            account_email=email,
            clearance_grade=3,
            modules=["COMMON", "*"],
            is_admin=True,
        )
        await repository.upsert_access(access)
        print(f"[fab_agent] 관리자 권한 부트스트랩: {email}", flush=True)
        return access

    raise AppException(
        status_code=403,
        message=(
            "지식 에이전트 접근 권한이 등록되지 않았습니다. "
            "관리자에게 권한 등록을 요청하세요."
        ),
    )
