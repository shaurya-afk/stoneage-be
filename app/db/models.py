import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, LargeBinary, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class ExtractionRaw(Base):
    __tablename__ = "extraction_raw"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    file_name: Mapped[str] = mapped_column(Text, nullable=False)
    file_content: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    document_type: Mapped[str] = mapped_column(Text, nullable=False)
    fields: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    llm_model: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    processed: Mapped[list["ExtractionProcessed"]] = relationship(
        "ExtractionProcessed",
        back_populates="raw",
        foreign_keys="ExtractionProcessed.raw_id",
    )


class ExtractionProcessed(Base):
    __tablename__ = "extraction_processed"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    raw_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("extraction_raw.id", ondelete="SET NULL"),
        nullable=True,
    )
    file_name: Mapped[str] = mapped_column(Text, nullable=False)
    document_type: Mapped[str] = mapped_column(Text, nullable=False)
    fields: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    response: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    llm_model: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    raw: Mapped["ExtractionRaw | None"] = relationship(
        "ExtractionRaw",
        back_populates="processed",
        foreign_keys=[raw_id],
    )
