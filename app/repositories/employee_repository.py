from collections.abc import Mapping, Sequence
from typing import Any
from uuid import UUID

from sqlalchemy import Select, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.employee import Employee

from app.core.constants import Department, EmployeeRole


class EmployeeRepository:
    """
    Database-access layer for Employee records.

    This class:
    - Builds and executes Employee queries.
    - Does not raise HTTP exceptions.
    - Does not contain business rules.
    - Flushes changes but lets the service control transaction commits.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, employee: Employee) -> Employee:
        self.db.add(employee)
        await self.db.flush()
        await self.db.refresh(employee)
        return employee

    async def get_by_id(self, employee_id: UUID) -> Employee | None:
        statement = select(Employee).where(Employee.id == employee_id)
        result = await self.db.execute(statement)
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> Employee | None:
        normalized_email = email.strip().lower()

        statement = select(Employee).where(
            func.lower(Employee.email) == normalized_email
        )
        result = await self.db.execute(statement)
        return result.scalar_one_or_none()

    async def get_by_employee_code(
        self,
        employee_code: str,
    ) -> Employee | None:
        normalized_code = employee_code.strip()

        statement = select(Employee).where(
            Employee.employee_code == normalized_code
        )
        result = await self.db.execute(statement)
        return result.scalar_one_or_none()

    def _apply_filters(
        self,
        statement: Select[Any],
        *,
        department: Department | None = None,
        role: EmployeeRole | None = None,
        designation: str | None = None,
        is_active: bool | None = None,
        search: str | None = None,
    ) -> Select[Any]:
        if department is not None:
            statement = statement.where(Employee.department == department)

        if role is not None:
            statement = statement.where(Employee.role == role)

        if designation:
            statement = statement.where(
                Employee.designation.ilike(f"%{designation.strip()}%")
            )

        if is_active is not None:
            statement = statement.where(Employee.is_active == is_active)

        if search:
            escaped_search = (
                search.strip()
                .replace("\\", "\\\\")
                .replace("%", "\\%")
                .replace("_", "\\_")
            )

            pattern = f"%{escaped_search}%"

            statement = statement.where(
                or_(
                    Employee.employee_code.ilike(pattern, escape="\\"),
                    Employee.full_name.ilike(pattern, escape="\\"),
                    Employee.email.ilike(pattern, escape="\\"),
                    Employee.designation.ilike(pattern, escape="\\"),
                )
            )

        return statement

    async def list(
        self,
        *,
        department: Department | None = None,
        role: EmployeeRole | None = None,
        designation: str | None = None,
        is_active: bool | None = None,
        search: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[Sequence[Employee], int]:
        data_statement = select(Employee)

        data_statement = self._apply_filters(
            data_statement,
            department=department,
            role=role,
            designation=designation,
            is_active=is_active,
            search=search,
        )

        data_statement = (
            data_statement
            .order_by(
                Employee.created_at.desc(),
                Employee.id.desc(),
            )
            .limit(limit)
            .offset(offset)
        )

        data_result = await self.db.execute(data_statement)
        employees = data_result.scalars().all()

        count_statement = select(func.count(Employee.id))

        count_statement = self._apply_filters(
            count_statement,
            department=department,
            role=role,
            designation=designation,
            is_active=is_active,
            search=search,
        )

        count_result = await self.db.execute(count_statement)
        total = count_result.scalar_one()

        return employees, total

    async def update(
        self,
        employee: Employee,
        updates: Mapping[str, Any],
    ) -> Employee:
        for field_name, value in updates.items():
            setattr(employee, field_name, value)

        await self.db.flush()
        await self.db.refresh(employee)
        return employee

    async def delete(self, employee: Employee) -> None:
        await self.db.delete(employee)
        await self.db.flush()