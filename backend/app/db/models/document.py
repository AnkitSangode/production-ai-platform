from __future__ import annotations

from datetime import datetime
from uuid import  uuid4,UUID

from sqlalchemy import DateTime, ForeignKey, Integer, String, Enum
from sqlalchemy import UUID as SQLAlchemyUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

from typing import TYPE_CHECKING

from app.enums.document import DocumentStatus

if TYPE_CHECKING:
    from app.db.models.user import User


class Document(Base):
    __tablename__ = "documents"

    # -------------------------
    # Identity
    # -------------------------

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4,
    )

    # -------------------------
    # Ownership
    # -------------------------

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
    )

    # -------------------------
    # File Metadata
    # -------------------------

    original_filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    storage_key: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        unique=True,
    )

    content_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    file_size: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    page_count: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    # -------------------------
    # Processing
    # -------------------------

    status: Mapped[DocumentStatus] = mapped_column(
        Enum(DocumentStatus),
        default=DocumentStatus.UPLOADED,
        nullable=False,
    )

    error_message: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True,
    )

    processing_worker_id: Mapped[UUID | None] = mapped_column(
        SQLAlchemyUUID(as_uuid=True),
        nullable=True,
    )

    processing_lease_expiry: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # -------------------------
    # Audit
    # -------------------------

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.now,
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.now,
        onupdate=datetime.now,
        nullable=False,
    )

    # -------------------------
    # Relationships
    # -------------------------

    user: Mapped["User"] = relationship(
        back_populates="documents",
    )