# Core
from core.manager import BaseManager


class HealthcheckManager(BaseManager):

    async def check_db_conection(self) -> bool:
        result = await self._db().command("ping")
        return result.get("ok") == 1.0


class Healthcheck:
    objects = HealthcheckManager()
