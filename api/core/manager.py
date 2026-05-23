# Integrations
from integrations.mongo import get_mongo_db


class BaseManager:
    """Base class for every ``<Feature>Manager`` in the project.

    Provides shared helpers for accessing MongoDB so subclasses don't import
    :func:`integrations.mongo.get_mongo_db` directly.

    Two kinds of managers are supported:

    1. **Collection-bound managers** (e.g. ``UserManager``) — declare a
       ``COLLECTION`` class attribute and use :meth:`_col` in their queries.
    2. **Database-only managers** (e.g. ``HealthcheckManager``) — leave
       ``COLLECTION`` as ``None`` and use :meth:`_db` to issue commands that
       are not scoped to a single collection.
    """

    COLLECTION: str | None = None

    def _db(self):
        """Return the active MongoDB database handle."""
        return get_mongo_db()

    def _col(self):
        """Return the collection bound to this manager.

        Raises:
            RuntimeError: If the subclass did not declare ``COLLECTION``.
        """
        if self.COLLECTION is None:
            raise RuntimeError(
                f"{type(self).__name__} did not define COLLECTION"
            )
        return self._db()[self.COLLECTION]
