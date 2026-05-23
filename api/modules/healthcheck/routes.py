# FastApi
import fastapi

# Module
from modules.healthcheck.manager import Healthcheck


router = fastapi.APIRouter(prefix="/healthcheck")


@router.get(
    "",
    tags=["healthcheck"],
    summary="Get Health Check of application",
    responses={
        200: {
            "description": "Created route response.",
            "content": {"application/json": {"example": {"status": "ok", "db": "ok"}}},
        },
    },
)
async def healthcheck() -> dict:
    """It is responsible for verifying the API status and its MongoDB connection."""
    db_ok = await Healthcheck.objects.check_db_conection()
    return {"status": "ok", "db": "ok" if db_ok else "down"}
