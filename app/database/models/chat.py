"""Chat sessions/messages -- chat_sessions.id doubles as the LangGraph
thread_id if you wire up AsyncPostgresSaver for conversation checkpoints."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import ENUM as PGEnum
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.constants import ChatRole
from app.database.base import Base, TimestampMixin, UUIDPKMixin

if TYPE_CHECKING:
    from app.database.models.employee import Employee

chat_role_enum = PGEnum(
    ChatRole,
    name="chat_role_enum",
    values_callable=lambda enum_cls: [e.value for e in enum_cls],
)


class ChatSession(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "chat_sessions"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str | None] = mapped_column(String(300))

    user: Mapped["Employee"] = relationship()
    messages: Mapped[list["ChatMessage"]] = relationship(
        back_populates="session", cascade="all, delete-orphan", order_by="ChatMessage.created_at"
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<ChatSession {self.id} user_id={self.user_id}>"


class ChatMessage(UUIDPKMixin, Base):
    __tablename__ = "chat_messages"

    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role: Mapped[ChatRole] = mapped_column(chat_role_enum, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)

    # [{blog_id, title, author, department, published_at, snippet, url}, ...]
    citations: Mapped[list | None] = mapped_column(JSONB)
    # retrieved chunk/image ids + scores -- for debugging and eval, not shown to the user
    retrieval_debug: Mapped[dict | None] = mapped_column(JSONB)

    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)

    session: Mapped["ChatSession"] = relationship(back_populates="messages")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<ChatMessage session_id={self.session_id} role={self.role}>"