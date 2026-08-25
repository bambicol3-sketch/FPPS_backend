from app.domains.pdf_to_ppt.domain.value_object.slide_outline import SlideOutline

MAX_SLIDES = 20
MAX_BULLETS_PER_SLIDE = 6
MAX_BULLET_LENGTH = 200
MAX_TITLE_LENGTH = 80


class OutlineLimits:
    """LLM 이 생성한 슬라이드 개요가 렌더링 가능한 범위를 벗어나지 않도록 방어한다."""

    @staticmethod
    def clamp(slides: list[SlideOutline]) -> list[SlideOutline]:
        clamped: list[SlideOutline] = []
        for slide in slides[:MAX_SLIDES]:
            title = (slide.title or "").strip()[:MAX_TITLE_LENGTH] or "슬라이드"
            bullets = [
                bullet.strip()[:MAX_BULLET_LENGTH]
                for bullet in (slide.bullets or [])
                if bullet and bullet.strip()
            ][:MAX_BULLETS_PER_SLIDE]
            clamped.append(SlideOutline(title=title, bullets=bullets))
        return clamped
