# Python
from datetime import datetime
from enum import Enum
from typing import Annotated

# Libs
from pydantic import BaseModel, ConfigDict, Field

# Constants
from constants.funds import FundValidationMessages


class Categoria(str, Enum):
    """Business categorization of a fund.

    ``FPV`` (Fondo de Pensiones Voluntarias) and ``FIC`` (Fondo de
    Inversión Colectiva) are the two product families the platform
    supports. Stored as their string value so Mongo documents and JWT
    claims stay human-readable.
    """

    FPV = "FPV"
    FIC = "FIC"


class PerfilRiesgo(str, Enum):
    """Risk profile of a fund — optional dimension used for filtering."""

    BAJO = "BAJO"
    MODERADO = "MODERADO"
    ALTO = "ALTO"


class FundResponseDTO(BaseModel):
    """Public projection of a fund — the canonical read shape.

    Returned by ``GET /funds``, ``POST /admin/funds`` and by
    :meth:`FundManager.get_fund_by_id`. Kept as the single read shape so
    consumers (HTTP clients, the future subscriptions module) only need
    to know one schema.
    """

    id: int
    nombre: str
    monto_minimo: int
    categoria: Categoria
    descripcion: str | None = None
    perfil_riesgo: PerfilRiesgo | None = None
    activo: bool
    created_at: datetime
    updated_at: datetime


class FundListResponseDTO(BaseModel):
    """Paginated wrapper used as the ``GET /funds`` response body.

    Carries the total document count alongside the page so clients can
    render pagination controls without a follow-up count request.
    """

    items: list[FundResponseDTO]
    total: int
    skip: int
    limit: int


class CreateFundRequestDTO(BaseModel):
    """Body of ``POST /admin/funds``.

    Validation lives entirely in Pydantic so the manager only sees
    already-clean values. ``str_strip_whitespace`` mirrors the convention
    used by the auth module, keeping ``nombre`` lookups deterministic.
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    id: int = Field(..., gt=0, description="Numeric primary key. Stored as Mongo _id.")
    nombre: str = Field(..., min_length=3, max_length=100)
    monto_minimo: int = Field(..., gt=0, description=FundValidationMessages.MONTO_MINIMO_POSITIVE)
    categoria: Categoria
    descripcion: str | None = Field(default=None, max_length=500)
    perfil_riesgo: PerfilRiesgo | None = None


class FundFilterParams(BaseModel):
    """Query parameters accepted by ``GET /funds``.

    Bundled as a Pydantic model so FastAPI parses + validates them in one
    step, and so the manager can stay framework-agnostic by receiving a
    plain ``dict`` of filters instead of N keyword arguments.
    """

    categoria: Categoria | None = None
    perfil_riesgo: PerfilRiesgo | None = None
    skip: Annotated[int, Field(ge=0)] = 0
    limit: Annotated[int, Field(ge=1, le=100)] = 20

    def to_filters(self) -> dict:
        """Project the optional filters into a Mongo-ready ``$and`` dict.

        Pagination params (``skip``/``limit``) are excluded since they are
        passed separately to the manager. Returning only set fields keeps
        the resulting query compact and explicit.
        """
        filters: dict = {}
        if self.categoria is not None:
            filters["categoria"] = self.categoria.value
        if self.perfil_riesgo is not None:
            filters["perfil_riesgo"] = self.perfil_riesgo.value
        return filters


class DeleteFundResponseDTO(BaseModel):
    """Response body for ``DELETE /admin/funds/{fund_id}``."""

    message: str
    fund_id: int
