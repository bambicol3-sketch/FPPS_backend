import logging
from datetime import date, datetime, timedelta, timezone
from typing import List

from app.domains.macro.application.port.ddakjubu_file_reader_port import DdakjubuFileReaderPort
from app.domains.macro.application.port.macro_transcript_fetch_port import MacroTranscriptFetchPort
from app.domains.macro.application.port.macro_video_fetch_port import MacroVideoFetchPort
from app.domains.macro.application.port.market_risk_cache_port import MarketRiskCachePort
from app.domains.macro.application.port.market_risk_llm_port import MarketRiskLlmPort
from app.domains.macro.application.response.market_risk_response import (
    MarketRiskResponse,
    ReferencedVideoItem,
)
from app.domains.macro.domain.entity.market_risk_assessment import RiskStance
from app.domains.macro.domain.entity.reference_video import ReferenceVideo
from app.domains.macro.domain.service.market_risk_prompt_builder import MarketRiskPromptBuilder

logger = logging.getLogger(__name__)

DDAKJUBU_CHANNEL_IDS: List[str] = [
    "UC2-YdiOkgqWzIdDwCYW1utw",  # 딱딱한 주식 부드럽게 | 딱주부TV
]

RECENT_DAYS = 7
MAX_VIDEOS_PER_CHANNEL = 10
MAX_VIDEOS_FOR_PROMPT = 5
CACHE_TTL_SECONDS = 3600


class AssessMarketRiskUseCase:
    """ddakjubu.md와 딱주부TV 최근 7일 영상을 참고해 오늘의 Risk-on/Risk-off를 판단한다."""

    def __init__(
        self,
        ddakjubu_file_reader_port: DdakjubuFileReaderPort,
        video_fetch_port: MacroVideoFetchPort,
        transcript_fetch_port: MacroTranscriptFetchPort,
        market_risk_llm_port: MarketRiskLlmPort,
        cache_port: MarketRiskCachePort,
    ):
        self._file_reader = ddakjubu_file_reader_port
        self._video_fetch_port = video_fetch_port
        self._transcript_fetch_port = transcript_fetch_port
        self._llm_port = market_risk_llm_port
        self._cache_port = cache_port
        self._prompt_builder = MarketRiskPromptBuilder()

    async def execute(self) -> MarketRiskResponse:
        today = datetime.now(timezone.utc).date()

        cached = await self._cache_port.get(today)
        if cached is not None:
            logger.info("[macro_risk] 캐시 적중 as_of=%s stance=%s", today, cached.stance)
            return cached

        ddakjubu_content = self._file_reader.read_content()
        ddakjubu_used = bool(ddakjubu_content.strip())

        videos = await self._collect_recent_videos()
        videos = sorted(videos, key=lambda v: v.published_at, reverse=True)[
            :MAX_VIDEOS_FOR_PROMPT
        ]
        await self._populate_transcripts(videos)

        if not ddakjubu_used and not videos:
            note = "참고 컨텍스트 없음: ddakjubu.md가 비어있고 최근 7일 영상도 없음."
            logger.info("[macro_risk] %s", note)
            return MarketRiskResponse(
                as_of=today,
                stance=RiskStance.UNKNOWN.value,
                reason_summary=[],
                referenced_videos=[],
                ddakjubu_md_used=False,
                note=note,
            )

        user_prompt = self._prompt_builder.build(
            as_of=today,
            ddakjubu_md_content=ddakjubu_content,
            reference_videos=videos,
        )

        try:
            llm_result = await self._llm_port.ask(
                system_instructions=self._prompt_builder.SYSTEM_INSTRUCTIONS,
                user_prompt=user_prompt,
            )
        except Exception as e:
            logger.error("[macro_risk] LLM 호출 실패: %s", e)
            return MarketRiskResponse(
                as_of=today,
                stance=RiskStance.UNKNOWN.value,
                reason_summary=[],
                referenced_videos=self._to_ref_items(videos),
                ddakjubu_md_used=ddakjubu_used,
                note=f"LLM 호출 실패: {type(e).__name__}",
            )

        stance = self._normalize_stance(llm_result.stance)
        reasons = self._limit_reasons(llm_result.reasons)

        response = MarketRiskResponse(
            as_of=today,
            stance=stance.value,
            reason_summary=reasons,
            referenced_videos=self._to_ref_items(videos),
            ddakjubu_md_used=ddakjubu_used,
            note="",
        )

        if stance != RiskStance.UNKNOWN:
            await self._cache_port.save(today, response, CACHE_TTL_SECONDS)

        return response

    async def _collect_recent_videos(self) -> List[ReferenceVideo]:
        if not DDAKJUBU_CHANNEL_IDS:
            return []
        published_after = datetime.now(timezone.utc) - timedelta(days=RECENT_DAYS)
        try:
            return await self._video_fetch_port.fetch_recent_videos(
                channel_ids=DDAKJUBU_CHANNEL_IDS,
                published_after=published_after,
                max_per_channel=MAX_VIDEOS_PER_CHANNEL,
            )
        except Exception as e:
            logger.warning("[macro_risk] 영상 조회 실패: %s", e)
            return []

    async def _populate_transcripts(self, videos: List[ReferenceVideo]) -> None:
        for video in videos:
            try:
                video.transcript = await self._transcript_fetch_port.fetch_transcript(
                    video.video_id
                )
            except Exception as e:
                logger.warning(
                    "[macro_risk] 자막 추출 실패 video_id=%s error=%s",
                    video.video_id,
                    e,
                )
                video.transcript = ""

    @staticmethod
    def _to_ref_items(videos: List[ReferenceVideo]) -> List[ReferencedVideoItem]:
        return [
            ReferencedVideoItem(
                video_id=v.video_id,
                title=v.title,
                published_at=v.published_at.strftime("%Y-%m-%d"),
            )
            for v in videos
        ]

    @staticmethod
    def _normalize_stance(raw: str) -> RiskStance:
        if not raw:
            return RiskStance.UNKNOWN
        value = raw.strip().lower().replace("_", "-")
        mapping = {
            "risk-on": RiskStance.RISK_ON,
            "riskon": RiskStance.RISK_ON,
            "risk on": RiskStance.RISK_ON,
            "risk-off": RiskStance.RISK_OFF,
            "riskoff": RiskStance.RISK_OFF,
            "risk off": RiskStance.RISK_OFF,
            "neutral": RiskStance.NEUTRAL,
            "unknown": RiskStance.UNKNOWN,
        }
        return mapping.get(value, RiskStance.UNKNOWN)

    BLOCKED_SOURCE_TERMS = (
        "딱주부TV",
        "딱주부tv",
        "딱주부",
        "딱딱한 주식 부드럽게",
        "딱딱한주식부드럽게",
        "ddakjubu",
        "DdakjubuTV",
    )

    REPORTING_ENDINGS = (
        ("강조함", "강조하고 있습니다"),
        ("시사함", "시사하고 있습니다"),
        ("평가함", "평가되고 있습니다"),
        ("해석함", "해석되고 있습니다"),
        ("설명함", "설명되고 있습니다"),
        ("권고함", "권장되고 있습니다"),
        ("밝힘", "확인되고 있습니다"),
        ("전함", "전해지고 있습니다"),
        ("언급함", "언급되고 있습니다"),
        ("제시함", "제시되고 있습니다"),
        ("판정하고 있음", "판단되고 있습니다"),
        ("강조됨", "강조되고 있습니다"),
        ("시사됨", "시사되고 있습니다"),
        ("평가됨", "평가되고 있습니다"),
        ("해석됨", "해석되고 있습니다"),
        ("설명됨", "설명되고 있습니다"),
        ("권고됨", "권장되고 있습니다"),
        ("언급됨", "언급되고 있습니다"),
        ("제시됨", "제시되고 있습니다"),
        ("확인됨", "확인되고 있습니다"),
        ("관찰됨", "관찰되고 있습니다"),
    )

    @classmethod
    def _limit_reasons(cls, reasons: List[str]) -> List[str]:
        cleaned: List[str] = []
        for raw in reasons or []:
            if not raw:
                continue
            sanitized = cls._sanitize_reason(raw)
            if sanitized:
                cleaned.append(sanitized)
        return cleaned[:5]

    @classmethod
    def _sanitize_reason(cls, text: str) -> str:
        import re
        result = text
        for term in cls.BLOCKED_SOURCE_TERMS:
            result = result.replace(term, "최근 시장 분석 자료")
        result = cls._fix_benchmark_index_name(result)
        result = re.sub(r"\s{2,}", " ", result).strip(" -·:|,")
        result = cls._normalize_ending(result)
        return result.strip()

    @staticmethod
    def _fix_benchmark_index_name(text: str) -> str:
        """문장에 800~950 범위 포인트가 등장하면 '코스피'를 '코스피200'으로 교정한다.

        해당 범위 숫자는 벤치마크 지수 코스피200의 포인트이므로, '코스피' 단독 표기는 부정확하다.
        '코스피200', '코스피 200', 'KOSPI200', 'KOSPI 200' 등 이미 200이 붙은 경우는 건드리지 않는다.
        """
        import re
        benchmark_level_pattern = re.compile(r"(?<!\d)(8[0-9]{2}|9[0-4][0-9]|950)(?!\d)")
        if not benchmark_level_pattern.search(text):
            return text
        kospi_bare_pattern = re.compile(r"코스피(?!\s*200)(?!200)")
        return kospi_bare_pattern.sub("코스피200", text)

    @classmethod
    def _normalize_ending(cls, text: str) -> str:
        trimmed = text.rstrip()
        trailing_punct = ""
        while trimmed and trimmed[-1] in ".。":
            trailing_punct = trimmed[-1] + trailing_punct
            trimmed = trimmed[:-1]

        for bad, good in cls.REPORTING_ENDINGS:
            if trimmed.endswith(bad):
                trimmed = trimmed[: -len(bad)] + good
                break

        if not trailing_punct:
            trailing_punct = "."
        return trimmed + trailing_punct
