"""Request/response schemas for app/routers/blog.py."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.core.constants import BlogStatus, BlogVisibility, Department
from app.schemas.common import EmployeeBrief


class AttachmentBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    file_name: str
    file_type: str
    processing_status: str


class ImageBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    thumbnail_url: str
    caption: str | None = None


# ---- POST /blogs --------------------------------------------------------------

class BlogCreateRequest(BaseModel):
    title: str = Field(max_length=300)
    content: str
    visibility: BlogVisibility = BlogVisibility.COMPANY_WIDE
    status: BlogStatus = BlogStatus.DRAFT


class BlogCreateResponse(BaseModel):
    id: uuid.UUID
    slug: str
    status: BlogStatus
    processing_status: str = "pending"
    created_at: datetime


# ---- GET /blogs (list/browse) --------------------------------------------------

class BlogListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    summary: str | None = None
    author: EmployeeBrief
    department: Department
    published_at: datetime | None = None
    thumbnail_url: str | None = None


class BlogListResponse(BaseModel):
    items: list[BlogListItem]
    total: int
    page: int
    page_size: int


# ---- GET /blogs/{id} ------------------------------------------------------------

class BlogDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    slug: str
    content: str
    summary: str | None = None
    author: EmployeeBrief
    department: Department
    status: BlogStatus
    visibility: BlogVisibility
    attachments: list[AttachmentBrief] = []
    images: list[ImageBrief] = []
    current_version: int
    view_count: int
    created_at: datetime
    updated_at: datetime
    published_at: datetime | None = None


# ---- PUT /blogs/{id} --------------------------------------------------------------

class BlogUpdateRequest(BaseModel):
    title: str = Field(max_length=300)
    content: str
    change_note: str | None = None


class BlogUpdateResponse(BaseModel):
    id: uuid.UUID
    current_version: int
    processing_status: str = "pending"


# ---- PATCH /blogs/{id}/status --------------------------------------------------

class BlogStatusUpdateRequest(BaseModel):
    status: BlogStatus


class BlogStatusUpdateResponse(BaseModel):
    id: uuid.UUID
    status: BlogStatus
    published_at: datetime | None = None


# ---- DELETE /blogs/{id} -----------------------------------------------------------

class BlogDeleteResponse(BaseModel):
    id: uuid.UUID
    status: BlogStatus = BlogStatus.DELETED
    deleted_at: datetime


# ---- GET /blogs/{id}/versions, GET /blogs/{id}/versions/{version_number} ----------

class BlogVersionListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    version_number: int
    title: str
    edited_by: EmployeeBrief
    change_note: str | None = None
    created_at: datetime


class BlogVersionListResponse(BaseModel):
    items: list[BlogVersionListItem]


class BlogVersionDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    version_number: int
    title: str
    content: str
    edited_by: EmployeeBrief
    change_note: str | None = None
    created_at: datetime