from uuid import UUID, uuid4

from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

from app.db.models.document import Document


class User(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4,
    )

    name: Mapped[str]

    documents: Mapped[list["Document"]] = relationship(
        back_populates="user"
    )