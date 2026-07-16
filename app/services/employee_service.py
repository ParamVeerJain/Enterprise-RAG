import logging
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.exc import DBAPIError, IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.employee import Employee
from app.core.constants import Department,EmployeeRole
from app.repositories.employee_repository import EmployeeRepository
from app.schemas.employee_schema import EmployeeCreate, EmployeePatch

logger = logging.getLogger(__name__)


class EmployeeServiceError(Exception):
    """Base exception for employee-service errors."""


class EmployeeNotFoundError(EmployeeServiceError):
    def __init__(self, employee_id: UUID) -> None:
        self.employee_id = employee_id
        super().__init__(f"Employee '{employee_id}' was not found")


class EmployeeConflictError(EmployeeServiceError):
    def __init__(self, message: str, *, field: str | None = None) -> None:
        self.field = field
        super().__init__(message)


class EmployeeValidationError(EmployeeServiceError):
    """Raised when a business-level validation rule fails."""


class EmployeeDatabaseError(EmployeeServiceError):
    """Raised when an unexpected database operation fails."""


@dataclass(slots=True)
class EmployeePage:
    items: list[Employee]
    total: int
    limit: int
    offset: int


class EmployeeService:
    """
    Business layer for Employee operations.

    The service owns transaction boundaries. Repository methods only flush;
    this service commits or rolls back the complete operation.
    """

    def __init__(
        self,
        db: AsyncSession,
        repository: EmployeeRepository | None = None,
    ) -> None:
        self.db = db
        self.repository = repository or EmployeeRepository(db)

    async def create_employee(self, payload: EmployeeCreate) -> Employee:
        normalized_email = str(payload.email).strip().lower()
        normalized_code = payload.employee_code.strip()

        existing_email = await self.repository.get_by_email(normalized_email)
        if existing_email is not None:
            raise EmployeeConflictError(
                "An employee with this email already exists",
                field="email",
            )

        existing_code = await self.repository.get_by_employee_code(
            normalized_code
        )
        if existing_code is not None:
            raise EmployeeConflictError(
                "An employee with this employee code already exists",
                field="employee_code",
            )

        employee = Employee(
            employee_code=normalized_code,
            full_name=payload.full_name.strip(),
            email=normalized_email,
            password_hash=payload.password_hash,
            department=payload.department,
            role=payload.role,
            designation=payload.designation,
            is_active=payload.is_active,
        )

        try:
            employee = await self.repository.create(employee)
            await self.db.commit()
            return employee

        except IntegrityError as exc:
            await self.db.rollback()

            logger.info(
                "Employee creation violated a unique/database constraint",
                exc_info=exc,
            )

            raise self._translate_integrity_error(exc) from exc

        except SQLAlchemyError as exc:
            await self.db.rollback()

            logger.exception(
                "Unexpected database error while creating employee"
            )

            raise EmployeeDatabaseError(
                "The employee could not be created due to a database error"
            ) from exc

    async def get_employee(self, employee_id: UUID) -> Employee:
        try:
            employee = await self.repository.get_by_id(employee_id)
        except SQLAlchemyError as exc:
            logger.exception(
                "Database error while retrieving employee %s",
                employee_id,
            )
            raise EmployeeDatabaseError(
                "The employee could not be retrieved"
            ) from exc

        if employee is None:
            raise EmployeeNotFoundError(employee_id)

        return employee

    async def get_employees(
        self,
        *,
        department: Department | None = None,
        role: EmployeeRole | None = None,
        designation: str | None = None,
        is_active: bool | None = None,
        search: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> EmployeePage:
        if limit < 1 or limit > 100:
            raise EmployeeValidationError(
                "limit must be between 1 and 100"
            )

        if offset < 0:
            raise EmployeeValidationError(
                "offset cannot be negative"
            )

        normalized_search = search.strip() if search else None
        normalized_designation = (
            designation.strip() if designation else None
        )

        try:
            employees, total = await self.repository.list(
                department=department,
                role=role,
                designation=normalized_designation,
                is_active=is_active,
                search=normalized_search,
                limit=limit,
                offset=offset,
            )
        except SQLAlchemyError as exc:
            logger.exception("Database error while listing employees")
            raise EmployeeDatabaseError(
                "Employees could not be retrieved"
            ) from exc

        return EmployeePage(
            items=list(employees),
            total=total,
            limit=limit,
            offset=offset,
        )

    async def patch_employee(
        self,
        employee_id: UUID,
        payload: EmployeePatch,
    ) -> Employee:
        employee = await self.get_employee(employee_id)

        updates = payload.model_dump(exclude_unset=True)

        if not updates:
            raise EmployeeValidationError(
                "At least one field must be provided for update"
            )

        if updates.get("employee_code") is None and "employee_code" in updates:
            raise EmployeeValidationError(
                "employee_code cannot be null"
            )

        if updates.get("full_name") is None and "full_name" in updates:
            raise EmployeeValidationError(
                "full_name cannot be null"
            )

        if updates.get("email") is None and "email" in updates:
            raise EmployeeValidationError(
                "email cannot be null"
            )

        if updates.get("password_hash") is None and "password_hash" in updates:
            raise EmployeeValidationError(
                "password_hash cannot be null"
            )

        if updates.get("department") is None and "department" in updates:
            raise EmployeeValidationError(
                "department cannot be null"
            )

        if updates.get("role") is None and "role" in updates:
            raise EmployeeValidationError(
                "role cannot be null"
            )

        if updates.get("is_active") is None and "is_active" in updates:
            raise EmployeeValidationError(
                "is_active cannot be null"
            )

        if "email" in updates:
            normalized_email = str(updates["email"]).strip().lower()
            email_owner = await self.repository.get_by_email(normalized_email)

            if email_owner is not None and email_owner.id != employee_id:
                raise EmployeeConflictError(
                    "Another employee already uses this email",
                    field="email",
                )

            updates["email"] = normalized_email

        if "employee_code" in updates:
            normalized_code = updates["employee_code"].strip()
            code_owner = await self.repository.get_by_employee_code(
                normalized_code
            )

            if code_owner is not None and code_owner.id != employee_id:
                raise EmployeeConflictError(
                    "Another employee already uses this employee code",
                    field="employee_code",
                )

            updates["employee_code"] = normalized_code

        if "full_name" in updates:
            updates["full_name"] = updates["full_name"].strip()

        try:
            employee = await self.repository.update(employee, updates)
            await self.db.commit()
            return employee

        except IntegrityError as exc:
            await self.db.rollback()

            logger.info(
                "Employee update violated a unique/database constraint",
                exc_info=exc,
            )

            raise self._translate_integrity_error(exc) from exc

        except SQLAlchemyError as exc:
            await self.db.rollback()

            logger.exception(
                "Database error while updating employee %s",
                employee_id,
            )

            raise EmployeeDatabaseError(
                "The employee could not be updated"
            ) from exc

    async def delete_employee(self, employee_id: UUID) -> None:
        employee = await self.get_employee(employee_id)

        try:
            await self.repository.delete(employee)
            await self.db.commit()

        except IntegrityError as exc:
            await self.db.rollback()

            logger.info(
                "Employee %s could not be deleted because it is referenced",
                employee_id,
                exc_info=exc,
            )

            raise EmployeeConflictError(
                "Employee cannot be deleted because other records depend on it"
            ) from exc

        except DBAPIError as exc:
            await self.db.rollback()

            logger.exception(
                "Database API error while deleting employee %s",
                employee_id,
            )

            raise EmployeeDatabaseError(
                "The employee could not be deleted"
            ) from exc

        except SQLAlchemyError as exc:
            await self.db.rollback()

            logger.exception(
                "Database error while deleting employee %s",
                employee_id,
            )

            raise EmployeeDatabaseError(
                "The employee could not be deleted"
            ) from exc

    @staticmethod
    def _translate_integrity_error(
        exc: IntegrityError,
    ) -> EmployeeConflictError:
        """
        Convert database constraint violations into safe service errors.

        Constraint names vary between databases, so this checks the underlying
        error text without returning raw database details to API clients.
        """

        error_text = str(exc.orig).lower()

        if "email" in error_text:
            return EmployeeConflictError(
                "An employee with this email already exists",
                field="email",
            )

        if "employee_code" in error_text:
            return EmployeeConflictError(
                "An employee with this employee code already exists",
                field="employee_code",
            )

        return EmployeeConflictError(
            "Employee data conflicts with an existing database record"
        )