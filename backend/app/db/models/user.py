from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.document import Document


class User(Base):
    __tablename__ = "users"

    # -------------------------
    # Identity
    # -------------------------

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4,
    )

    # -------------------------
    # Profile
    # -------------------------

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    # -------------------------
    # Authentication
    # -------------------------

    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
    )

    hashed_password: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    # -------------------------
    # Account State
    # -------------------------

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    is_verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
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

    documents: Mapped[list["Document"]] = relationship(
        back_populates="user",
    )