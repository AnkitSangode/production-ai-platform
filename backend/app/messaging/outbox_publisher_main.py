from app.db.session import SessionLocal
from app.uow.unit_of_work import UnitOfWork


def create_unit_of_work() -> UnitOfWork:
    return UnitOfWork(SessionLocal())