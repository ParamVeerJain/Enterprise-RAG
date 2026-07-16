"""The two vector indexes: text chunks (bge-m3) and image embeddings (SigLIP2).

Both use bigint identity PKs (not UUID) -- these rows are internal, never
addressed directly by clients, and there are far more of them than any other
table, so a compact key is worth it. blog_id is a plain foreign key: a blog
has however many chunk rows its content needs, from 1 to several hundred --
see Section 6 of the architecture doc for the worked example.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from pgvector.sqlalchemy import Vector
from sqlalchemy import BigInteger, Computed, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import ENUM as PGEnum
from sqlalchemy.dialects.postgresql import TSVECTOR, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.constants import ChunkSourceType
from app.database.base import Base

if TYPE_CHECKING:
    from app.database.models.attachment import Image
    from app.database.models.blog import Blog

# Dimensions must match whatever embedding models you actually deploy --
# 1024 for bge-m3, 1152 for siglip2-so400m. If you swap models, these change
# too, and existing rows need re-embedding (see Section 7 of the doc).
TEXT_EMBEDDING_DIM = 1024
IMAGE_EMBEDDING_DIM = 1152

chunk_source_type_enum = PGEnum(
    ChunkSourceType,
    name="chunk_source_type_enum",
    values_callable=lambda enum_cls: [e.value for e in enum_cls],
)


class Chunk(Base):
    """The text / sentence-transformer index."""

    __tablename__ = "chunks"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    blog_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("blogs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source_type: Mapped[ChunkSourceType] = mapped_column(chunk_source_type_enum, nullable=False, index=True)
    # Polymorphic: attachment_id or image_id depending on source_type. No hard
    # FK here on purpose -- it can point at either table.
    source_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))

    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False)
    token_count: Mapped[int | None] = mapped_column(Integer)

    embedding: Mapped[list[float]] = mapped_column(Vector(TEXT_EMBEDDING_DIM), nullable=False)
    embedding_model: Mapped[str] = mapped_column(String(80), nullable=False)

    blog_version: Mapped[int] = mapped_column(Integer, nullable=False)

    # Generated column powering hybrid (keyword) search alongside the vector
    # search -- Postgres maintains this automatically on INSERT/UPDATE.
    tsv: Mapped[str] = mapped_column(
        TSVECTOR, Computed("to_tsvector('english', chunk_text)", persisted=True)
    )

    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)

    blog: Mapped["Blog"] = relationship(back_populates="chunks")

    __table_args__ = (
        Index(
            "ix_chunks_embedding_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_with={"m": 16, "ef_construction": 64},
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
        Index("ix_chunks_tsv_gin", "tsv", postgresql_using="gin"),
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Chunk blog_id={self.blog_id} idx={self.chunk_index} source={self.source_type}>"


class ImageEmbedding(Base):
    """The multimodal / CLIP-family index -- a different space and dimension
    from Chunk.embedding, hence a separate table rather than a shared one."""

    __tablename__ = "image_embeddings"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    image_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("images.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    # Denormalized for fast filtering without a join back through images -> blogs.
    blog_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("blogs.id", ondelete="CASCADE"), nullable=False, index=True
    )

    embedding: Mapped[list[float]] = mapped_column(Vector(IMAGE_EMBEDDING_DIM), nullable=False)
    embedding_model: Mapped[str] = mapped_column(String(80), nullable=False)

    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)

    image: Mapped["Image"] = relationship(back_populates="embedding")

    __table_args__ = (
        Index(
            "ix_image_embeddings_embedding_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_with={"m": 16, "ef_construction": 64},
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<ImageEmbedding image_id={self.image_id}>"