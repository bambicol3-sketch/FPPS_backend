from datetime import datetime

from sqlalchemy import DateTime, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.database import Base


class MethodologyOrm(Base):
    __tablename__ = "ddakjubu2_methodologies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    video_id: Mapped[str] = mapped_column(
        String(50), nullable=False, unique=True, index=True
    )
    video_title: Mapped[str] = mapped_column(Text, nullable=False, default="")
    methodology: Mapped[dict] = mapped_column(JSON, nullable=False)
    extracted_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    model: Mapped[str] = mapped_column(String(50), nullable=False, default="")
