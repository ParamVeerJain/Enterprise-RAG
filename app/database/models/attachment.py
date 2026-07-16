"""Attachments (uploaded files), their per-page text, and images.

images covers BOTH directly-uploaded pictures (attachment_id NULL) and
images extracted from a PDF/PPTX/DOCX (attachment_id set) -- one table,
one downstream pipeline (OCR + caption + CLIP embed) for both cases.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Boolean, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import ENUM as PGEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.constants import AttachmentFileType, ProcessingStatus
from app.database.base import Base, TimestampMixin, UUIDPKMixin

if TYPE_CHECKING:
    from app.database.models.blog import Blog
    from app.database.models.chunk import ImageEmbedding
    from app.database.models.employee import Employee

file_type_enum = PGEnum(
    AttachmentFileType,
    name="attachment_file_type_enum",
    values_callable=lambda enum_cls: [e.value for e in enum_cls],
)
# Shared with chat.py? No -- attachments and images each get their own status
# enum instance name to keep migrations independent, even though the Python
# enum (ProcessingStatus) is the same.
processing_status_enum = PGEnum(
    ProcessingStatus,
    name="processing_status_enum",
    values_callable=lambda enum_cls: [e.value for e in enum_cls],
)


class Attachment(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "attachments"

    blog_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("blogs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    file_name: Mapped[str] = mapped_column(String(500), nullable=False)
    file_type: Mapped[AttachmentFileType] = mapped_column(file_type_enum, nullable=False)
    storage_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    mime_type: Mapped[str | None] = mapped_column(String(120))
    size_bytes: Mapped[int | None] = mapped_column(BigInteger)
    page_count: Mapped[int | None] = mapped_column(Integer)
    is_scanned: Mapped[bool | None] = mapped_column(Boolean)  # set after parsing

    processing_status: Mapped[ProcessingStatus] = mapped_column(
        processing_status_enum, nullable=False, default=ProcessingStatus.PENDING, index=True
    )
    processing_error: Mapped[str | None] = mapped_column(Text)

    uploaded_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("employees.id"), nullable=False
    )

    blog: Mapped["Blog"] = relationship(back_populates="attachments")
    uploader: Mapped["Employee"] = relationship(foreign_keys=[uploaded_by])
    pages: Mapped[list["AttachmentPage"]] = relationship(
        back_populates="attachment", cascade="all, delete-orphan", order_by="AttachmentPage.page_number"
    )
    images: Mapped[list["Image"]] = relationship(back_populates="attachment", cascade="all, delete-orphan")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Attachment {self.file_name} status={self.processing_status}>"


class AttachmentPage(UUIDPKMixin, Base):
    """Enables page-level citation, e.g. 'page 4 of the Q3 report'."""

    __tablename__ = "attachment_pages"

    attachment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("attachments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    raw_text: Mapped[str | None] = mapped_column(Text)  # native text-layer extraction
    ocr_text: Mapped[str | None] = mapped_column(Text)  # filled only if OCR fallback ran
    thumbnail_path: Mapped[str | None] = mapped_column(String(1000))

    attachment: Mapped["Attachment"] = relationship(back_populates="pages")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<AttachmentPage attachment_id={self.attachment_id} page={self.page_number}>"


class Image(UUIDPKMixin, Base):
    __tablename__ = "images"

    blog_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("blogs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    attachment_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("attachments.id", ondelete="CASCADE"), index=True
    )
    source_page: Mapped[int | None] = mapped_column(Integer)

    storage_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    width: Mapped[int | None] = mapped_column(Integer)
    height: Mapped[int | None] = mapped_column(Integer)
    alt_text: Mapped[str | None] = mapped_column(String(500))
    ocr_text: Mapped[str | None] = mapped_column(Text)  # text physically printed in the image
    caption: Mapped[str | None] = mapped_column(Text)  # VLM-generated description
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)

    blog: Mapped["Blog"] = relationship(back_populates="images")
    attachment: Mapped["Attachment | None"] = relationship(back_populates="images")
    embedding: Mapped["ImageEmbedding | None"] = relationship(
        back_populates="image", cascade="all, delete-orphan", uselist=False
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Image {self.storage_path}>"