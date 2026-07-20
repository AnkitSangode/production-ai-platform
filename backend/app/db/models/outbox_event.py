from app.db.base import Base

from uuid import UUID,uuid4

from sqlalchemy.orm import Mapped,mapped_column

from sqlalchemy import ForeignKey, String, DateTime, Enum, func

from sqlalchemy.dialects.postgresql import JSONB

from datetime import datetime

from app.enums.outbox import EventType



class OutboxEvent(Base):
    __tablename__ = "outbox_events"

    id: Mapped[UUID] = mapped_column(
        primary_key= True,
        default= uuid4
    )

    document_id: Mapped[UUID] = mapped_column(
        ForeignKey("documents.id"),
        nullable= False
    )

    event_type: Mapped[EventType] = mapped_column(
        Enum(EventType),
        nullable=False  
    )

    payload: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable= False
    )

    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )