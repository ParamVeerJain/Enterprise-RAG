"""Request/response schemas for app/routers/attachment.py.

POST /blogs/{id}/attachments itself takes multipart/form-data (files), not
a JSON body, so there's no Pydantic "request" model for it -- FastAPI takes
`files: list[UploadFile]` directly in the path function signature.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.core.constants import AttachmentFileType, ProcessingStatus


class AttachmentAccepted(BaseModel):
    attachment_id: uuid.UUID
    file_name: str
    file_type: AttachmentFileType
    processing_status: ProcessingStatus = ProcessingStatus.PENDING


class AttachmentUploadResponse(BaseModel):
    attachments: list[AttachmentAccepted]


class AttachmentListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    file_name: str
    file_type: AttachmentFileType
    size_bytes: int | None = None
    page_count: int | None = None
    is_scanned: bool | None = None
    processing_status: ProcessingStatus
    created_at: datetime


class AttachmentListResponse(BaseModel):
    items: list[AttachmentListItem]


class AttachmentStatusResponse(BaseModel):
    id: uuid.UUID
    processing_status: ProcessingStatus
    processing_error: str | None = None