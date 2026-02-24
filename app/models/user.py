import uuid

from sqlalchemy import DateTime, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    api_key: Mapped[str] = mapped_column(String, unique=True, nullable=False, index=True)
    timezone: Mapped[str] = mapped_column(String, nullable=False, default="UTC")
    created_at = mapped_column(DateTime(timezone=True), server_default=func.now())
