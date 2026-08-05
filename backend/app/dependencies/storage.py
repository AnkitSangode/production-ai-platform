from functools import lru_cache

from app.core.config import get_settings
from app.storage.base import StorageService
from app.storage.local import LocalStorageService


@lru_cache
def get_storage_service() -> StorageService:
    return LocalStorageService(get_settings())