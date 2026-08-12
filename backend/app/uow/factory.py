from contextlib import contextmanager
from collections.abc import Iterator

from app.db.session import SessionLocal
from app.uow.unit_of_work import UnitOfWork


@contextmanager
def create_unit_of_work() -> Iterator[UnitOfWork]:
    db = SessionLocal()
    uow = UnitOfWork(db)

    try:
        yield uow
    except Exception:
        uow.rollback()
        raise
    finally:
        uow.close()