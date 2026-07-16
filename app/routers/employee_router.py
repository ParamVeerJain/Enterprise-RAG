import logging
from typing import Annotated
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.constants import Department, EmployeeRole
from app.database.session import get_db
from app.schemas.employee_schema import (
    EmployeeCreate,
    EmployeeListResponse,
    EmployeePatch,
    EmployeeResponse,
)
from app.services.employee_service import (
    EmployeeConflictError,
    EmployeeDatabaseError,
    EmployeeNotFoundError,
    EmployeeService,
    EmployeeValidationError,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/employees",
    tags=["Employees"],
)


async def get_employee_service(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> EmployeeService:
    return EmployeeService(db=db)


EmployeeServiceDependency = Annotated[
    EmployeeService,
    Depends(get_employee_service),
]


def handle_employee_service_exception(exc: Exception) -> None:
    """
    Translate service exceptions into safe HTTP responses.

    Raw SQL/database errors are deliberately not exposed to API clients.
    """

    if isinstance(exc, EmployeeNotFoundError):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "EMPLOYEE_NOT_FOUND",
                "message": str(exc),
            },
        ) from exc

    if isinstance(exc, EmployeeConflictError):
        detail: dict[str, str] = {
            "code": "EMPLOYEE_CONFLICT",
            "message": str(exc),
        }

        if exc.field is not None:
            detail["field"] = exc.field

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=detail,
        ) from exc

    if isinstance(exc, EmployeeValidationError):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "EMPLOYEE_VALIDATION_ERROR",
                "message": str(exc),
            },
        ) from exc

    if isinstance(exc, EmployeeDatabaseError):
        logger.error(
            "Employee operation failed because of a database error",
            exc_info=exc,
        )

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "EMPLOYEE_DATABASE_ERROR",
                "message": (
                    "The employee service is temporarily unavailable"
                ),
            },
        ) from exc

    logger.exception(
        "Unhandled error in employee endpoint",
        exc_info=exc,
    )

    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail={
            "code": "INTERNAL_SERVER_ERROR",
            "message": "An unexpected error occurred",
        },
    ) from exc


@router.post(
    "",
    response_model=EmployeeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create an employee",
    responses={
        409: {"description": "Email or employee code already exists"},
        422: {"description": "Request validation failed"},
        503: {"description": "Database is unavailable"},
    },
)
async def create_employee(
    payload: EmployeeCreate,
    service: EmployeeServiceDependency,
) -> EmployeeResponse:
    try:
        employee = await service.create_employee(payload)
        return EmployeeResponse.model_validate(employee)

    except Exception as exc:
        handle_employee_service_exception(exc)
        raise  # Unreachable, but helps static type checkers.


@router.get(
    "",
    response_model=EmployeeListResponse,
    summary="List and filter employees",
    responses={
        422: {"description": "Invalid filter or pagination value"},
        503: {"description": "Database is unavailable"},
    },
)
async def get_employees(
    service: EmployeeServiceDependency,
    department: Annotated[
        Department | None,
        Query(description="Filter by exact department"),
    ] = None,
    role: Annotated[
        EmployeeRole | None,
        Query(description="Filter by exact employee role"),
    ] = None,
    designation: Annotated[
        str | None,
        Query(
            min_length=1,
            max_length=120,
            description="Case-insensitive partial designation match",
        ),
    ] = None,
    is_active: Annotated[
        bool | None,
        Query(description="Filter active or inactive employees"),
    ] = None,
    search: Annotated[
        str | None,
        Query(
            min_length=1,
            max_length=150,
            description=(
                "Search employee code, name, email, or designation"
            ),
        ),
    ] = None,
    limit: Annotated[
        int,
        Query(
            ge=1,
            le=100,
            description="Maximum employees returned",
        ),
    ] = 50,
    offset: Annotated[
        int,
        Query(
            ge=0,
            description="Number of employees to skip",
        ),
    ] = 0,
) -> EmployeeListResponse:
    try:
        page = await service.get_employees(
            department=department,
            role=role,
            designation=designation,
            is_active=is_active,
            search=search,
            limit=limit,
            offset=offset,
        )

        return EmployeeListResponse(
            items=[
                EmployeeResponse.model_validate(employee)
                for employee in page.items
            ],
            total=page.total,
            limit=page.limit,
            offset=page.offset,
        )

    except Exception as exc:
        handle_employee_service_exception(exc)
        raise


@router.get(
    "/{employee_id}",
    response_model=EmployeeResponse,
    summary="Get an employee by ID",
    responses={
        404: {"description": "Employee not found"},
        422: {"description": "Invalid UUID"},
        503: {"description": "Database is unavailable"},
    },
)
async def get_employee(
    employee_id: UUID,
    service: EmployeeServiceDependency,
) -> EmployeeResponse:
    try:
        employee = await service.get_employee(employee_id)
        return EmployeeResponse.model_validate(employee)

    except Exception as exc:
        handle_employee_service_exception(exc)
        raise


@router.patch(
    "/{employee_id}",
    response_model=EmployeeResponse,
    summary="Partially update an employee",
    responses={
        404: {"description": "Employee not found"},
        409: {"description": "Email or employee code already exists"},
        422: {"description": "Request validation failed"},
        503: {"description": "Database is unavailable"},
    },
)
async def patch_employee(
    employee_id: UUID,
    payload: EmployeePatch,
    service: EmployeeServiceDependency,
) -> EmployeeResponse:
    try:
        employee = await service.patch_employee(employee_id, payload)
        return EmployeeResponse.model_validate(employee)

    except Exception as exc:
        handle_employee_service_exception(exc)
        raise


@router.delete(
    "/{employee_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an employee",
    responses={
        404: {"description": "Employee not found"},
        409: {
            "description": (
                "Employee is referenced by records that prevent deletion"
            )
        },
        503: {"description": "Database is unavailable"},
    },
)
async def delete_employee(
    employee_id: UUID,
    service: EmployeeServiceDependency,
) -> Response:
    try:
        await service.delete_employee(employee_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    except Exception as exc:
        handle_employee_service_exception(exc)
        raise