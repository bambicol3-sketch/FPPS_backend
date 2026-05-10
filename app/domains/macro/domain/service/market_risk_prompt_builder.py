from datetime import date
from typing import List

from app.domains.macro.domain.entity.reference_video import ReferenceVideo


class MarketRiskPromptBuilder:
    """ddakjubu.md 파일 내용과 최근 유튜브 영상을 결합해 Risk-on/Risk-off 판단 프롬프트를 생성한다.

    순수 도메인 서비스 — 외부 의존성 없음.
    """

    SYSTEM_INSTRUCTIONS = (
        "너는 사용자에게 오늘의 시장 상태를 친절하게 설명해 주는 매크로 애널리스트다. "
        "참고 컨텍스트(학습 노트와 최근 유튜브 영상)를 내부 근거로만 사용하고, "
        "응답은 네가 직접 판단해 설명해 주는 것처럼 자연스러운 말투로 작성한다. "
        "반드시 지정된 JSON 스키마로만 응답한다.\n\n"
        "지수 명칭 정확성 규칙 (매우 중요):\n"
        "- 참고 컨텍스트에서 800~950 범위의 포인트 숫자(예: 865, 870, 880, 890, 900, 920)는 "
        "벤치마크 지수인 **코스피200(KOSPI 200)** 의 포인트이다. 일반 지수 '코스피(KOSPI)' 가 아니다.\n"
        "- 이 범위 포인트를 언급할 때는 반드시 '코스피200' 으로 명확히 표기할 것. "
        "절대 '코스피'로만 표기하지 말 것.\n"
        "- 일반 종합지수 '코스피'는 통상 2,400~3,000 포인트대이므로, 800~900 포인트를 '코스피'라고 부르면 오류이다.\n"
        "- 코스피200 선물·옵션, 베이시스, 프로그램 매매 등 파생 관련 언급 시에도 '코스피200' 표기를 유지한다.\n\n"
        "저작권 및 출처 표현 규칙:\n"
        "- 응답 문장에 '딱주부', '딱주부TV', '딱딱한 주식 부드럽게', 'ddakjubu' 같은 특정 채널·프로그램 이름을 절대 언급하지 말 것.\n"
        "- '~라고 강조함', '~라고 시사함', '~라고 평가함', '~라고 해석함', '~라고 설명함', "
        "'~라고 권고함', '~라고 밝힘', '~라고 전함', '~라고 언급함', '~라고 제시함', "
        "'~라고 판정하고 있음' 등 제삼자 발언을 전달하는 듯한 간접 인용·보고 어미는 사용하지 말 것.\n"
        "- 대신 네가 직접 관찰·판단해 사용자에게 설명하듯이 작성한다.\n\n"
        "어미·말투 규칙:\n"
        "- 각 문장은 '~입니다', '~있습니다', '~보입니다', '~나타나고 있습니다', '~되고 있습니다' 같은 "
        "직설적이고 친절한 해요체/합쇼체 평서문 어미로 마무리한다.\n"
        "- '~함', '~됨', '~임' 같은 개조식 어미는 금지한다."
    )

    RESPONSE_SCHEMA_GUIDE = """반드시 다음 JSON 형식으로만 응답하라. 다른 텍스트, 주석, 코드펜스 금지.

{
  "stance": "Risk-on" | "Risk-off" | "Neutral" | "Unknown",
  "reasons": [
    "이유 1 (한 문장)",
    "이유 2 (한 문장)"
  ]
}

규칙:
- stance는 네 값 중 하나만 사용
- reasons 배열은 최대 5개 항목, 각 항목은 한 문장
- reasons에는 '딱주부', '딱주부TV', '딱딱한 주식 부드럽게', 'ddakjubu' 등 특정 채널/프로그램 이름을 포함하지 말 것
- reasons의 어미는 '~입니다', '~있습니다', '~보입니다', '~나타나고 있습니다' 같은 직접 설명형 평서문만 사용
- '~강조함', '~시사함', '~평가함', '~해석함', '~설명함', '~권고함', '~밝힘', '~전함', '~언급함', '~판정하고 있음' 같은 간접 인용·보고 어미 금지
- 참고 컨텍스트가 불충분하면 stance는 "Unknown"

좋은 예:
- "코스피200이 870에서 890까지 주요 저항선을 차례로 돌파하며 목표 구간이 한 단계 위로 올라간 모습이 나타나고 있습니다."
- "반도체 섹터가 상대적으로 강한 흐름을 유지하고 있어 보유자 입장에서는 구조적 안정성이 확인되고 있습니다."

나쁜 예 (사용 금지):
- "코스피가 870→880→890 구간을 통과하며..." (800~900대 포인트는 '코스피'가 아니라 '코스피200' 이다)
- "~라고 강조함."
- "~보유자 기준의 안정성을 강조함."
- "~매수 수요가 유효함을 시사함."
"""

    def build(
        self,
        as_of: date,
        ddakjubu_md_content: str,
        reference_videos: List[ReferenceVideo],
    ) -> str:
        as_of_str = as_of.strftime("%Y-%m-%d")

        file_section = self._format_file_section(ddakjubu_md_content)
        video_section = self._format_video_section(reference_videos)

        return (
            f"[오늘 일자] {as_of_str}\n\n"
            f"[참고 컨텍스트 A — 딱주부 학습 노트 (ddakjubu.md)]\n{file_section}\n\n"
            f"[참고 컨텍스트 B — 딱주부TV 최근 7일 영상]\n{video_section}\n\n"
            f"[질문]\n"
            f"위 두 참고 컨텍스트만을 근거로, 오늘({as_of_str}) 기준 한국/글로벌 주식 시장이 "
            f"Risk-on 상태인지 Risk-off 상태인지 판단하고, 그 이유를 5줄 이내로 요약하라.\n\n"
            f"{self.RESPONSE_SCHEMA_GUIDE}"
        )

    @staticmethod
    def _format_file_section(content: str) -> str:
        trimmed = (content or "").strip()
        if not trimmed:
            return "(ddakjubu.md 비어있음 — 해당 참고 컨텍스트 없음)"
        if len(trimmed) > 8000:
            trimmed = trimmed[:8000] + "\n...(이하 생략)"
        return trimmed

    @staticmethod
    def _format_video_section(videos: List[ReferenceVideo]) -> str:
        if not videos:
            return "(최근 7일 업로드된 참고 가능한 영상 없음)"
        blocks = [video.short_context() for video in videos]
        return "\n\n---\n\n".join(blocks)
