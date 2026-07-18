from datetime import datetime

from sqlalchemy import DateTime, Integer, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.database import Base


class MasterMethodologyOrm(Base):
    __tablename__ = "ddakjubu2_master_methodology"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    methodology: Mapped[dict] = mapped_column(JSON, nullable=False)
    source_video_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
