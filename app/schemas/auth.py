"""Request/response schemas for app/routers/auth.py."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.core.constants import Department, EmployeeRole


# ---- POST /auth/login ------------------------------------------------------

class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)


class LoggedInUser(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    full_name: str
    email: EmailStr
    department: Department
    role: EmployeeRole
    designation: str | None = None


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: LoggedInUser


# ---- POST /auth/refresh ----------------------------------------------------

class RefreshRequest(BaseModel):
    refresh_token: str


class RefreshResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


# ---- POST /auth/logout ------------------------------------------------------

class LogoutRequest(BaseModel):
    refresh_token: str


# ---- GET /auth/me ------------------------------------------------------------

class MeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    employee_code: str
    full_name: str
    email: EmailStr
    department: Department
    role: EmployeeRole
    designation: str | None = None
    is_active: bool
    last_login_at: datetime | None = None


# ---- POST /auth/change-password ---------------------------------------------

class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str = Field(min_length=8)


# ---- POST /auth/forgot-password ---------------------------------------------

class ForgotPasswordRequest(BaseModel):
    email: EmailStr


# ---- POST /auth/reset-password -----------------------------------------------

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(min_length=8)