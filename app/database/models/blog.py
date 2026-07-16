"""Blog + version-history tables."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import ENUM as PGEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.constants import BlogStatus, BlogVisibility, Department
from app.database.base import Base, TimestampMixin, UUIDPKMixin
from app.database.models.employee import department_enum

if TYPE_CHECKING:
    from app.database.models.attachment import Attachment, Image
    from app.database.models.chunk import Chunk
    from app.database.models.employee import Employee

blog_status_enum = PGEnum(
    BlogStatus,
    name="blog_status_enum",
    values_callable=lambda enum_cls: [e.value for e in enum_cls],
)
blog_visibility_enum = PGEnum(
    BlogVisibility,
    name="blog_visibility_enum",
    values_callable=lambda enum_cls: [e.value for e in enum_cls],
)


class Blog(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "blogs"

    title: Mapped[str] = mapped_column(String(300), nullable=False)
    slug: Mapped[str] = mapped_column(String(320), unique=True, nullable=False, index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str | None] = mapped_column(Text)

    author_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("employees.id"), nullable=False, index=True
    )
    # Denormalized from author.department at creation time for fast filtering
    # (WHERE department = ... without a join). Kept in sync by the service
    # layer if the post is ever reassigned; not FK-tied to employees.department.
    department: Mapped[Department] = mapped_column(department_enum, nullable=False, index=True)

    status: Mapped[BlogStatus] = mapped_column(
        blog_status_enum, nullable=False, default=BlogStatus.DRAFT, index=True
    )
    visibility: Mapped[BlogVisibility] = mapped_column(
        blog_visibility_enum, nullable=False, default=BlogVisibility.COMPANY_WIDE
    )

    current_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    view_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    published_at: Mapped[datetime | None]
    deleted_at: Mapped[datetime | None]  # soft delete -- see Section 8 of the architecture doc

    # See the async-loading note in employee.py -- use selectinload()/joinedload()
    # at the query site rather than relying on implicit lazy access.
    author: Mapped["Employee"] = relationship(back_populates="blogs", foreign_keys=[author_id])
    versions: Mapped[list["BlogVersion"]] = relationship(
        back_populates="blog", cascade="all, delete-orphan", order_by="BlogVersion.version_number"
    )
    attachments: Mapped[list["Attachment"]] = relationship(
        back_populates="blog", cascade="all, delete-orphan"
    )
    images: Mapped[list["Image"]] = relationship(back_populates="blog", cascade="all, delete-orphan")
    chunks: Mapped[list["Chunk"]] = relationship(back_populates="blog", cascade="all, delete-orphan")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Blog {self.slug} status={self.status}>"


class BlogVersion(UUIDPKMixin, Base):
    __tablename__ = "blog_versions"

    blog_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("blogs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)

    edited_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("employees.id"), nullable=False
    )
    change_note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)

    blog: Mapped["Blog"] = relationship(back_populates="versions")
    editor: Mapped["Employee"] = relationship(
        back_populates="edited_versions", foreign_keys=[edited_by]
    )

    __table_args__ = (
        # one row per (blog_id, version_number) -- never two versions with the same number
        UniqueConstraint("blog_id", "version_number", name="uq_blog_version"),
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<BlogVersion blog_id={self.blog_id} v{self.version_number}>"