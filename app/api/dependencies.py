from functools import lru_cache

from fastapi import Depends

from app.services.sybil_service import SybilService


@lru_cache()
def _sybil_service_singleton() -> SybilService:
    # Singleton instance for now; in later steps this can be wired with
    # settings, DB session factories, graph caches, etc.
    return SybilService()


def get_sybil_service() -> SybilService:
    """Shared dependency for Sybil business logic."""
    return _sybil_service_singleton()


SybilServiceDependency = Depends(get_sybil_service)
