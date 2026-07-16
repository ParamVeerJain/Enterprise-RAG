from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

# These enums are already imported/available inside employee.py.
# Change this import if your enums live in a separate enum module.

from app.core.constants import Department, EmployeeRole


class EmployeeBase(BaseModel):
    employee_code: str = Field(
        min_length=1,
        max_length=30,
        examples=["EMP-1001"],
    )
    full_name: str = Field(
        min_length=1,
        max_length=150,
        examples=["Veer Jain"],
    )
    email: EmailStr
    department: Department
    role: EmployeeRole = EmployeeRole.EMPLOYEE
    designation: str | None = Field(
        default=None,
        max_length=120,
        examples=["Software Engineer"],
    )
    is_active: bool = True
    @field_validator("employee_code", "full_name")
    @classmethod
    def strip_required_strings(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Value cannot be empty or contain only whitespace")
        return value
    @field_validator("designation")
    @classmethod
    def strip_optional_designation(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None


class EmployeeCreate(EmployeeBase):
    """
    The service expects password_hash, not a plain-text password.

    When authentication is implemented, replace this field with `password`
    and hash it inside an authentication/password service.
    """
    password_hash: str = Field(
        min_length=1,
        description="Pre-hashed employee password. Never returned in responses.",
    )
    @field_validator("password_hash")
    @classmethod
    def validate_password_hash(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Password hash cannot be empty")

        return value


class EmployeePatch(BaseModel):
    """
    All fields are optional because this schema is used with HTTP PATCH.

    Only explicitly provided fields are updated through
    model_dump(exclude_unset=True).
    """
    employee_code: str | None = Field(default=None, min_length=1, max_length=30)
    full_name: str | None = Field(default=None, min_length=1, max_length=150)
    email: EmailStr | None = None
    password_hash: str | None = Field(default=None, min_length=1)
    department: Department | None = None
    role: EmployeeRole | None = None
    designation: str | None = Field(default=None, max_length=120)
    is_active: bool | None = None
    @field_validator("employee_code", "full_name", "password_hash")
    @classmethod
    def strip_non_nullable_strings(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("Value cannot be empty or contain only whitespace")
        return value
    @field_validator("designation")
    @classmethod
    def strip_designation(cls, value: str | None) -> str | None:
        if value is None:
            return None

        value = value.strip()
        return value or None


class EmployeeResponse(BaseModel):
    """
    Public employee representation.

    password_hash and relationship fields are intentionally excluded.
    """
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    employee_code: str
    full_name: str
    email: EmailStr
    department: Department
    role: EmployeeRole
    designation: str | None
    is_active: bool
    last_login_at: datetime | None
    created_at: datetime
    updated_at: datetime

class EmployeeListResponse(BaseModel):
    items: list[EmployeeResponse]
    total: int = Field(ge=0)
    limit: int = Field(ge=1)
    offset: int = Field(ge=0)