"""Employee identity + refresh-token tables.

Note: there is deliberately no separate `departments` table. Department is a
fixed, closed set of five values already defined as app.core.constants.Department,
so it's modeled as a native Postgres ENUM column directly on employees/blogs
rather than a lookup table with its own primary key. If that ever needs to
become dynamic (departments added/renamed at runtime), it should move to a
real table + FK at that point -- not before.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.dialects.postgresql import INET, UUID
from sqlalchemy.dialects.postgresql import ENUM as PGEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.constants import Department, EmployeeRole
from app.database.base import Base, TimestampMixin, UUIDPKMixin

if TYPE_CHECKING:
    from app.database.models.blog import Blog, BlogVersion

# Reused across employees.department and blogs.department so both columns
# share one Postgres enum type instead of two separately-named ones.
department_enum = PGEnum(
    Department,
    name="department_enum",
    values_callable=lambda enum_cls: [e.value for e in enum_cls],
)

employee_role_enum = PGEnum(
    EmployeeRole,
    name="employee_role_enum",
    values_callable=lambda enum_cls: [e.value for e in enum_cls],
)


class Employee(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "employees"
    employee_code: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(150), nullable=False)
    email: Mapped[str] = mapped_column(String(150), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    department: Mapped[Department] = mapped_column(department_enum, nullable=False)
    role: Mapped[EmployeeRole] = mapped_column(
        employee_role_enum, nullable=False, default=EmployeeRole.EMPLOYEE
    )
    designation: Mapped[str | None] = mapped_column(String(120))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_login_at: Mapped[datetime | None]

    # Async-loading note: relationships below default to lazy="select", which
    # does NOT work by simply accessing the attribute outside an active async
    # context. Load them explicitly per-query with selectinload()/joinedload()
    # from sqlalchemy.orm, e.g. select(Employee).options(selectinload(Employee.blogs)).
    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    blogs: Mapped[list["Blog"]] = relationship(
        back_populates="author", foreign_keys="Blog.author_id"
    )
    edited_versions: Mapped[list["BlogVersion"]] = relationship(
        back_populates="editor", foreign_keys="BlogVersion.edited_by"
    )
    def __repr__(self) -> str:  # pragma: no cover
        return f"<Employee {self.employee_code} {self.email}>"


class RefreshToken(UUIDPKMixin, Base):
    __tablename__ = "refresh_tokens"
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("employees.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    token_hash: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    issued_at: Mapped[datetime] = mapped_column(nullable=False)
    expires_at: Mapped[datetime] = mapped_column(nullable=False)
    revoked_at: Mapped[datetime | None]

    # Rotation chain: when a token is rotated, the *new* row's id goes here on
    # the *old* row, so reuse of an already-rotated token is detectable.
    replaced_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("refresh_tokens.id", ondelete="SET NULL"),
    )

    user_agent: Mapped[str | None] = mapped_column(String(300))
    ip_address: Mapped[str | None] = mapped_column(INET)

    user: Mapped["Employee"] = relationship(back_populates="refresh_tokens")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<RefreshToken user_id={self.user_id} revoked={self.revoked_at is not None}>"