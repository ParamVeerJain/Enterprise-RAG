"""Shared building blocks reused across every router's schemas."""

from __future__ import annotations

import uuid
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict

from app.core.constants import Department

T = TypeVar("T")


class EmployeeBrief(BaseModel):
    """The minimal employee shape embedded in blogs, versions, citations, etc."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    full_name: str
    department: Department | None = None


class MessageResponse(BaseModel):
    message: str


class Page(BaseModel, Generic[T]):
    """Generic paginated-list envelope. Usage: Page[BlogListItem]."""
    items: list[T]
    total: int
    page: int
    page_size: int


class PageParams(BaseModel):
    page: int = 1
    page_size: int = 20