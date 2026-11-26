"""Database engine, sessions and table creation.

Run `python -m flightdata.db` once to create the tables.
(Later, schema changes should move to Alembic migrations -- see docs/ROADMAP.md.)
"""

from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from .config import get_settings
from .models import Base


@lru_cache
def get_engine() -> Engine:
    return create_engine(get_settings().database_url, pool_pre_ping=True)


@lru_cache
def get_sessionmaker() -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(), expire_on_commit=False)


def get_session() -> Iterator[Session]:
    """FastAPI dependency: one session per request, closed afterwards."""
    with get_sessionmaker()() as session:
        yield session


def init_db() -> None:
    Base.metadata.create_all(get_engine())


if __name__ == "__main__":
    init_db()
    print("Tables created.")
