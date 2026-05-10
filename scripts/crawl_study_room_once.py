"""나딱구 공부방 대시보드를 1회 크롤링하여 DB 에 스냅샷으로 저장한다.

자격 증명은 영구 보관하지 않으며 실행 시점에만 사용된다.

사용 예
    python -m scripts.crawl_study_room_once
        ── 인터랙티브로 ID/PW 입력 (getpass 로 비밀번호 가림)

    python -m scripts.crawl_study_room_once --username foo --password bar
        ── CI 등 비대화형 환경에서 인자로 전달

    python -m scripts.crawl_study_room_once \
        --url https://jamesgong.duckdns.org/stock/dashboard/ \
        --username foo
        ── 비밀번호만 인터랙티브로 입력
"""

from __future__ import annotations

import argparse
import asyncio
import getpass
import sys
from pathlib import Path

# 프로젝트 루트를 import 경로에 추가하여 `python scripts/...` 직접 실행도 허용
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from sqlalchemy import text  # noqa: E402

from app.domains.study_room.adapter.outbound.external.study_room_dashboard_crawler import (  # noqa: E402
    StudyRoomDashboardCrawler,
)
from app.domains.study_room.adapter.outbound.persistence.dashboard_snapshot_repository_impl import (  # noqa: E402
    DashboardSnapshotRepositoryImpl,
)
from app.domains.study_room.application.usecase.crawl_study_room_dashboard_usecase import (  # noqa: E402
    CrawlStudyRoomDashboardUseCase,
)
import app.domains.study_room.infrastructure.orm.dashboard_snapshot_orm  # noqa: E402, F401
from app.infrastructure.database.database import AsyncSessionLocal, Base, engine  # noqa: E402


DEFAULT_DASHBOARD_URL = "https://jamesgong.duckdns.org/stock/dashboard/"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Crawl study_room dashboard once")
    parser.add_argument("--url", default=DEFAULT_DASHBOARD_URL, help="Dashboard URL")
    parser.add_argument("--username", default=None, help="Login username (omit to be prompted)")
    parser.add_argument("--password", default=None, help="Login password (omit to be prompted)")
    parser.add_argument("--login-url", default=None, help="Login form action URL (optional)")
    parser.add_argument(
        "--dump-html",
        default=None,
        metavar="PATH",
        help="크롤링한 HTML 을 해당 경로에 저장 (디버깅용)",
    )
    return parser.parse_args()


async def _ensure_table() -> None:
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)


async def _run(args: argparse.Namespace) -> int:
    username = args.username or input("study_room username: ").strip()
    password = args.password or getpass.getpass("study_room password: ")

    if not username or not password:
        print("자격 증명이 비어 있습니다. 크롤링을 중단합니다.", file=sys.stderr)
        return 2

    await _ensure_table()

    crawler = StudyRoomDashboardCrawler(
        dashboard_url=args.url,
        username=username,
        password=password,
        login_url=args.login_url,
    )

    async with AsyncSessionLocal() as db:
        repository = DashboardSnapshotRepositoryImpl(db)
        snapshot = await CrawlStudyRoomDashboardUseCase(crawler, repository).execute()

    if args.dump_html:
        dump_path = Path(args.dump_html)
        dump_path.parent.mkdir(parents=True, exist_ok=True)
        if crawler.last_fetched_html is not None:
            dump_path.write_text(crawler.last_fetched_html, encoding="utf-8")
            print(f"[dump] HTML saved to {dump_path} ({len(crawler.last_fetched_html)} chars)")
        else:
            print(
                "[dump] HTML 미저장: 인증 실패 또는 페이지 응답 자체가 없었습니다.",
                file=sys.stderr,
            )

    print(
        f"[done] status={snapshot.status.value} "
        f"stocks={len(snapshot.stock_metrics)} "
        f"industries={len(snapshot.leading_industries)} "
        f"sections={len(snapshot.sections)}"
    )
    if not snapshot.is_successful():
        print(f"[warn] error_reason={snapshot.error_reason}", file=sys.stderr)
        return 1
    return 0


def main() -> None:
    sys.exit(asyncio.run(_run(_parse_args())))


if __name__ == "__main__":
    main()
