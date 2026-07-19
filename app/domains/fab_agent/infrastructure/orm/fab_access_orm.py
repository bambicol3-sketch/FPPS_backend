from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.database import Base


class FabUserAccessOrm(Base):
    __tablename__ = "fab_user_access"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    account_email: Mapped[str] = mapped_column(
        String(255), nullable=False, unique=True, index=True
    )
    clearance_grade: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    modules: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    is_admin: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now
    )
