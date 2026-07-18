import re
from datetime import datetime
from typing import List, Optional

from app.domains.ddakjubu2.domain.entity.learning_note import LearningNote, StockInsight

VIDEO_ID_PATTERN = re.compile(r"video_id:\s*`([^`]+)`")
INSIGHT_TITLE_PATTERN = re.compile(r"^####\s+(.*?)(?:\s+\(([^)]*)\))?\s*$")


class LearningNoteMarkdownParser:
    """LearningNoteMarkdownFormatter 가 기록한 ddakjubu2.md 를 LearningNote 로 역파싱한다.

    백필(md → DB) 용도. 수동 추가 항목 등 형식 편차가 있으므로 관대하게 파싱하고,
    video_id 가 없는 블록은 건너뛴다.
    """

    def parse(self, content: str) -> List[LearningNote]:
        notes: List[LearningNote] = []
        blocks = self._split_blocks(content)
        for title, body_lines in blocks:
            note = self._parse_block(title, body_lines)
            if note is not None:
                notes.append(note)
        return notes

    @staticmethod
    def _split_blocks(content: str) -> List[tuple]:
        """'## ' 로 시작하는 라인을 기준으로 (제목, 본문 라인들) 블록을 나눈다."""
        blocks: List[tuple] = []
        current_title: Optional[str] = None
        current_lines: List[str] = []
        for line in content.splitlines():
            if line.startswith("## ") and not line.startswith("###"):
                if current_title is not None:
                    blocks.append((current_title, current_lines))
                current_title = line[3:].strip()
                current_lines = []
            elif current_title is not None:
                current_lines.append(line)
        if current_title is not None:
            blocks.append((current_title, current_lines))
        return blocks

    def _parse_block(self, title: str, lines: List[str]) -> Optional[LearningNote]:
        video_id = ""
        channel_name = ""
        program_category = ""
        published_at: Optional[datetime] = None
        learned_at: Optional[datetime] = None
        summary_lines: List[str] = []
        insights: List[StockInsight] = []

        section = ""  # "" | "summary" | "insights"
        current_insight: Optional[StockInsight] = None
        current_list: Optional[List[str]] = None  # 핵심 주장 / 근거 수집 대상

        for line in lines:
            stripped = line.strip()

            if stripped.startswith("### "):
                heading = stripped[4:].strip()
                if "핵심 요약" in heading:
                    section = "summary"
                elif "종목별 인사이트" in heading:
                    section = "insights"
                else:
                    section = ""
                current_insight = None
                current_list = None
                continue

            if stripped == "---":
                section = ""
                current_insight = None
                current_list = None
                continue

            if section == "insights" and stripped.startswith("#### "):
                match = INSIGHT_TITLE_PATTERN.match(stripped)
                if match:
                    current_insight = StockInsight(
                        stock_name=(match.group(1) or "").strip(),
                        ticker=(match.group(2) or "").strip(),
                        investment_view="",
                        key_claims=[],
                        supporting_evidence=[],
                    )
                    insights.append(current_insight)
                    current_list = None
                continue

            if section == "summary":
                if stripped:
                    summary_lines.append(stripped)
                continue

            if section == "insights" and current_insight is not None:
                if stripped.startswith("- 투자 관점:"):
                    current_insight.investment_view = stripped.split(":", 1)[1].strip()
                    current_list = None
                elif stripped.startswith("- 핵심 주장"):
                    current_list = current_insight.key_claims
                elif stripped.startswith("- 근거"):
                    current_list = current_insight.supporting_evidence
                elif stripped.startswith("- ") and current_list is not None:
                    current_list.append(stripped[2:].strip())
                continue

            # 메타데이터 (섹션 밖)
            if stripped.startswith("- video_id:"):
                found = VIDEO_ID_PATTERN.search(stripped)
                if found:
                    video_id = found.group(1).strip()
            elif stripped.startswith("- 채널:"):
                channel_name = stripped.split(":", 1)[1].strip()
            elif stripped.startswith("- 카테고리:"):
                program_category = stripped.split(":", 1)[1].strip()
            elif stripped.startswith("- 업로드일:"):
                published_at = self._parse_datetime(stripped.split(":", 1)[1].strip())
            elif stripped.startswith("- 학습일시:"):
                learned_at = self._parse_datetime(
                    stripped.split(":", 1)[1].strip(), with_time=True
                )

        if not video_id:
            return None

        fallback = learned_at or published_at or datetime(1970, 1, 1)
        return LearningNote(
            video_id=video_id,
            video_title=title,
            channel_name=channel_name,
            program_category=program_category or "전체영상",
            published_at=published_at or fallback,
            learned_at=learned_at or fallback,
            summary="\n".join(summary_lines).strip(),
            stock_insights=insights,
        )

    @staticmethod
    def _parse_datetime(raw: str, with_time: bool = False) -> Optional[datetime]:
        formats = ["%Y-%m-%d %H:%M", "%Y-%m-%d"] if with_time else ["%Y-%m-%d"]
        for fmt in formats:
            try:
                return datetime.strptime(raw, fmt)
            except ValueError:
                continue
        return None
