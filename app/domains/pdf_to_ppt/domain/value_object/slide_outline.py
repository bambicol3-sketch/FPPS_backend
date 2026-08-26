from dataclasses import dataclass, field


@dataclass(frozen=True)
class SlideOutline:
    title: str
    bullets: list[str] = field(default_factory=list)
