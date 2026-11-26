"""Reading and writing state vectors. All SQL lives here, so API and ingestion stay thin."""

from collections.abc import Sequence
from dataclasses import asdict
from datetime import UTC, datetime, timedelta

from sqlalchemy import and_, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from .geo import BoundingBox
from .models import StateVector
from .opensky_parser import StateRecord

# Rows per INSERT statement; keeps us far below the database's parameter limits.
CHUNK_SIZE = 500


def _insert_for(session: Session):
    """Pick the INSERT construct that supports ON CONFLICT for the current database."""
    dialect = session.get_bind().dialect.name
    if dialect == "postgresql":
        return pg_insert
    if dialect == "sqlite":
        return sqlite_insert
    raise NotImplementedError(f"Unsupported database dialect: {dialect}")


def store_states(session: Session, records: Sequence[StateRecord]) -> int:
    """Insert records, silently skipping ones we already have. Returns the number inserted."""
    if not records:
        return 0

    insert = _insert_for(session)
    inserted = 0
    for start in range(0, len(records), CHUNK_SIZE):
        rows = [asdict(record) for record in records[start : start + CHUNK_SIZE]]
        statement = (
            insert(StateVector)
            .values(rows)
            .on_conflict_do_nothing(index_elements=["icao24", "time_position"])
            .returning(StateVector.id)
        )
        inserted += len(session.execute(statement).scalars().all())
    session.commit()
    return inserted


def latest_states(
    session: Session,
    *,
    bbox: BoundingBox | None,
    max_age: timedelta,
    limit: int,
    now: datetime | None = None,
) -> list[StateVector]:
    """The newest known position of every aircraft seen within `max_age`."""
    cutoff = (now or datetime.now(UTC)) - max_age

    newest = (
        select(
            StateVector.icao24.label("icao24"),
            func.max(StateVector.time_position).label("max_time"),
        )
        .where(StateVector.time_position >= cutoff)
        .group_by(StateVector.icao24)
        .subquery()
    )
    statement = select(StateVector).join(
        newest,
        and_(
            StateVector.icao24 == newest.c.icao24,
            StateVector.time_position == newest.c.max_time,
        ),
    )
    if bbox is not None:
        statement = statement.where(
            StateVector.latitude.between(bbox.lamin, bbox.lamax),
            StateVector.longitude.between(bbox.lomin, bbox.lomax),
        )
    statement = statement.order_by(StateVector.icao24).limit(limit)
    return list(session.scalars(statement))


def track(
    session: Session,
    icao24: str,
    *,
    since: datetime | None,
    limit: int,
) -> list[StateVector]:
    """Positions of one aircraft in chronological order (the newest `limit` points)."""
    statement = select(StateVector).where(StateVector.icao24 == icao24.lower())
    if since is not None:
        statement = statement.where(StateVector.time_position >= since)
    statement = statement.order_by(StateVector.time_position.desc()).limit(limit)

    rows = list(session.scalars(statement))
    rows.reverse()
    return rows
