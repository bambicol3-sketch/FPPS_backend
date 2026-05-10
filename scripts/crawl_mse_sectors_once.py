"""나딱구 공부방 산업군 분석 페이지를 1회 크롤링하여 DB 에 스냅샷으로 저장한다.

자격 증명/쿠키는 영구 보관하지 않으며 실행 시점에만 사용된다.
"""

from __future__ import annotations

import argparse
import asyncio
import getpass
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from sqlalchemy import text  # noqa: E402

from app.domains.mse_sectors.adapter.outbound.external.mse_sectors_crawler import (  # noqa: E402
    SectorsCrawler,
)
from app.domains.mse_sectors.adapter.outbound.persistence.sectors_snapshot_repository_impl import (  # noqa: E402
    SectorsSnapshotRepositoryImpl,
)
from app.domains.mse_sectors.application.usecase.crawl_sectors_usecase import (  # noqa: E402
    CrawlSectorsUseCase,
)
import app.domains.mse_sectors.infrastructure.orm.sectors_snapshot_orm  # noqa: E402, F401
from app.infrastructure.database.database import AsyncSessionLocal, Base, engine  # noqa: E402


DEFAULT_PAGE_URL = "https://jamesgong.duckdns.org/stock/sectors/"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Crawl mse_sectors page once")
    parser.add_argument("--url", default=DEFAULT_PAGE_URL, help="Sectors page URL")
    parser.add_argument("--username", default=None, help="Login username (omit to be prompted)")
    parser.add_argument("--password", default=None, help="Login password (omit to be prompted)")
    parser.add_argument("--login-url", default=None, help="Login form action URL (optional)")
    parser.add_argument(
        "--cookie",
        default=None,
        help=(
            "브라우저에서 패스키 로그인 후 복사한 쿠키 문자열 "
            '(예: "session=abc; csrftoken=xyz"). 이 옵션을 주면 username/password 는 무시.'
        ),
    )
    parser.add_argument(
        "--dump-html",
        default=None,
        metavar="PATH",
        help="크롤링한 HTML 을 해당 경로에 저장 (디버깅용)",
    )
    return parser.parse_args()


def _parse_cookie_header(cookie_header: str) -> dict[str, str]:
    cookies: dict[str, str] = {}
    for piece in cookie_header.split(";"):
        piece = piece.strip()
        if not piece or "=" not in piece:
            continue
        name, _, value = piece.partition("=")
        cookies[name.strip()] = value.strip()
    return cookies


async def _ensure_table() -> None:
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)


async def _run(args: argparse.Namespace) -> int:
    cookies: dict[str, str] = {}
    username = ""
    password = ""

    if args.cookie:
        cookies = _parse_cookie_header(args.cookie)
        if not cookies:
            print("쿠키 파싱 실패. '이름=값; 이름2=값2' 형식으로 전달하세요.", file=sys.stderr)
            return 2
    else:
        username = args.username or input("mse_sectors username: ").strip()
        password = args.password or getpass.getpass("mse_sectors password: ")
        if not username or not password:
            print(
                "자격 증명/쿠키가 비어 있습니다. --cookie 또는 --username/--password 중 하나를 제공하세요.",
                file=sys.stderr,
            )
            return 2

    await _ensure_table()

    crawler = SectorsCrawler(
        page_url=args.url,
        username=username or None,
        password=password or None,
        login_url=args.login_url,
        cookies=cookies or None,
    )

    async with AsyncSessionLocal() as db:
        repository = SectorsSnapshotRepositoryImpl(db)
        snapshot = await CrawlSectorsUseCase(crawler, repository).execute()

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
