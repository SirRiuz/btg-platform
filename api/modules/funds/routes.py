# Python
from typing import Annotated

# FastApi
import fastapi
from fastapi import Depends, Query, status

# Constants
from constants.funds import FundMessages

# Module
from modules.auth.dependencies import get_current_user, require_role
from modules.auth.schemas import UserRole
from modules.funds.manager import Fund
from modules.funds.schemas import (
    Categoria,
    CreateFundRequestDTO,
    DeleteFundResponseDTO,
    FundFilterParams,
    FundListResponseDTO,
    FundResponseDTO,
    PerfilRiesgo,
)


# Two routers share the ``funds`` tag so they show up grouped in the OpenAPI
# UI, but they're mounted under distinct prefixes:
#   * ``/funds``        — any authenticated user (read-only catalog).
#   * ``/admin/funds``  — ADMIN-only (catalog management).
# Splitting them keeps each route's dependencies obvious at the file level and
# lines up with how the reverse proxy / API gateway will rate-limit these
# surfaces differently in production.
catalog_router = fastapi.APIRouter(prefix="/funds", tags=["funds"])
admin_router = fastapi.APIRouter(
    prefix="/admin/funds",
    tags=["funds"],
    dependencies=[Depends(require_role(UserRole.ADMIN))],
)


@catalog_router.get(
    "",
    status_code=status.HTTP_200_OK,
    response_model=FundListResponseDTO,
    summary="List active funds in the catalog",
)
async def list_funds(
    _: Annotated[dict, Depends(get_current_user)],
    categoria: Categoria | None = Query(default=None),
    perfil_riesgo: PerfilRiesgo | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
) -> FundListResponseDTO:
    """Return the paginated list of **active** funds visible to any user.

    Filters are optional and orthogonal — they narrow the same active-only
    base query the manager always enforces. Soft-deleted funds are
    invisible here by design: a future ``/admin/funds`` listing endpoint
    can expose them when there is a concrete operator need.

    The ``current_user`` is resolved purely to enforce authentication
    (any role is allowed); the user itself is not used in the query.
    """
    params = FundFilterParams(
        categoria=categoria,
        perfil_riesgo=perfil_riesgo,
        skip=skip,
        limit=limit,
    )
    items, total = await Fund.objects.list_active_funds(
        filters=params.to_filters(),
        skip=params.skip,
        limit=params.limit,
    )
    return FundListResponseDTO(
        items=items,
        total=total,
        skip=params.skip,
        limit=params.limit,
    )


@admin_router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=FundResponseDTO,
    summary="Create a new fund (ADMIN only)",
)
async def create_fund(payload: CreateFundRequestDTO) -> FundResponseDTO:
    """Persist a new fund in the catalog. ADMIN-only.

    Validation runs at three layers, fail-fast:

    1. :class:`CreateFundRequestDTO` (Pydantic) — types, ranges, lengths.
    2. :meth:`FundManager._find_conflict` — friendly 409 disambiguating
       id vs nombre collisions.
    3. The unique indexes on ``_id`` and ``nombre`` — final defense
       against races between concurrent creates.

    Raises:
        FundAlreadyExistsError: id or nombre already taken → ``409``.
        RequestValidationError: payload fails Pydantic validation → ``422``.
        InsufficientRoleError: caller is not an ADMIN → ``403``.
    """
    return await Fund.objects.create_fund(payload)


@admin_router.delete(
    "/{fund_id}",
    status_code=status.HTTP_200_OK,
    response_model=DeleteFundResponseDTO,
    summary="Soft-delete a fund (ADMIN only)",
)
async def delete_fund(fund_id: int) -> DeleteFundResponseDTO:
    """Mark a fund as inactive. ADMIN-only.

    Soft delete (``activo=False``) instead of physical removal because
    (a) funds will be referenced by future subscriptions and orphaning
    those rows would break historical reporting, (b) financial domains
    require trace preservation, (c) reactivation — if ever needed —
    becomes a single field flip.

    Raises:
        FundNotFoundError: no fund with ``fund_id`` → ``404``.
        FundAlreadyInactiveError: fund is already inactive → ``409``.
        InsufficientRoleError: caller is not an ADMIN → ``403``.
    """
    fund = await Fund.objects.soft_delete_fund(fund_id)
    return DeleteFundResponseDTO(
        message=FundMessages.FUND_DEACTIVATED.format(nombre=fund.nombre),
        fund_id=fund.id,
    )
