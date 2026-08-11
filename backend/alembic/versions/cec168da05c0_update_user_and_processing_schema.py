"""update user and processing schema

Revision ID: cec168da05c0
Revises: 0de85c80bb57
Create Date: 2026-08-11 17:56:17.495840

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "cec168da05c0"
down_revision: Union[str, Sequence[str], None] = "0de85c80bb57"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    document_status = sa.Enum(
        "UPLOADED",
        "PROCESSING",
        "READY",
        "FAILED",
        name="documentstatus",
    )

    document_status.create(op.get_bind(), checkfirst=True)

    op.alter_column(
        "documents",
        "status",
        existing_type=sa.VARCHAR(length=50),
        type_=document_status,
        existing_nullable=False,
        postgresql_using="status::text::documentstatus",
    )

    op.add_column(
        "outbox_events",
        sa.Column(
            "retry_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )

    op.add_column(
        "outbox_events",
        sa.Column(
            "worker_id",
            sa.String(length=255),
            nullable=True,
        ),
    )

    op.add_column(
        "outbox_events",
        sa.Column(
            "lease_expires_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )

    op.add_column(
        "users",
        sa.Column(
            "email",
            sa.String(length=255),
            nullable=False,
        ),
    )

    op.add_column(
        "users",
        sa.Column(
            "hashed_password",
            sa.String(length=255),
            nullable=False,
        ),
    )

    op.add_column(
        "users",
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
    )

    op.add_column(
        "users",
        sa.Column(
            "is_verified",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )

    op.add_column(
        "users",
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    op.add_column(
        "users",
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    op.create_index(
        op.f("ix_users_email"),
        "users",
        ["email"],
        unique=True,
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""

    op.drop_index(
        op.f("ix_users_email"),
        table_name="users",
    )

    op.drop_column("users", "updated_at")
    op.drop_column("users", "created_at")
    op.drop_column("users", "is_verified")
    op.drop_column("users", "is_active")
    op.drop_column("users", "hashed_password")
    op.drop_column("users", "email")

    op.drop_column("outbox_events", "lease_expires_at")
    op.drop_column("outbox_events", "worker_id")
    op.drop_column("outbox_events", "retry_count")

    op.alter_column(
        "documents",
        "status",
        existing_type=sa.Enum(
            "UPLOADED",
            "PROCESSING",
            "READY",
            "FAILED",
            name="documentstatus",
        ),
        type_=sa.VARCHAR(length=50),
        existing_nullable=False,
        postgresql_using="status::text",
    )

    sa.Enum(
        "UPLOADED",
        "PROCESSING",
        "READY",
        "FAILED",
        name="documentstatus",
    ).drop(op.get_bind(), checkfirst=True)
    # ### end Alembic commands ###
