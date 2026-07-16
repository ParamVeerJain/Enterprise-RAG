"""Audit trail for create/update/delete/login events.

Note the attribute is named `extra_data`, not `metadata` -- `metadata` is a
reserved attribute name on every declarative model (it's how SQLAlchemy
exposes the table's own MetaData object), so using it as a column name
would shadow that and raise an error at class-definition time. The actual
Postgres column is still named "metadata", via the explicit column-name
argument below.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import INET, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

if TYPE_CHECKING:
    from app.database.models.employee import Employee


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("employees.id", ondelete="SET NULL"), index=True
    )
    action: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    entity_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))

    extra_data: Mapped[dict | None] = mapped_column("metadata", JSONB)
    ip_address: Mapped[str | None] = mapped_column(INET)

    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False, index=True)

    user: Mapped["Employee | None"] = relationship()

    def __repr__(self) -> str:  # pragma: no cover
        return f"<AuditLog {self.action} {self.entity_type}={self.entity_id}>"