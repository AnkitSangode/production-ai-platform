from fastapi import Depends

from app.dependencies.parser import get_parser_service
from app.dependencies.storage import get_storage_service

from app.core.config import Settings, get_settings
from app.uow.unit_of_work import UnitOfWork
from app.dependencies.uow import get_unit_of_work
from app.services.document import DocumentService
from app.parser.base import ParserService
from app.storage.base import StorageService


def get_document_service(
    uow: UnitOfWork = Depends(get_unit_of_work),
    storage: StorageService = Depends(get_storage_service),
    parser: ParserService = Depends(get_parser_service),
    settings: Settings = Depends(get_settings),
) -> DocumentService:
    return DocumentService(
        uow=uow,
        storage=storage,
        parser=parser,
        settings=settings,
    )