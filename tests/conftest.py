"""Shared fixtures.

Heavy imports (SQLAlchemy, FastAPI) happen inside the fixtures, so tests that need neither
(like the parser tests) can run on their own. Database tests use an in-memory SQLite database,
so no PostgreSQL is needed to run the test suite.
"""

from datetime import UTC, datetime

import pytest


@pytest.fixture
def engine():
    from sqlalchemy import create_engine
    from sqlalchemy.pool import StaticPool

    from flightdata.models import Base

    # StaticPool: one shared connection, so the in-memory database survives across threads
    # (FastAPI runs sync endpoints in a thread pool).
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def session(engine):
    from sqlalchemy.orm import sessionmaker

    with sessionmaker(bind=engine, expire_on_commit=False)() as session:
        yield session


@pytest.fixture
def client(engine):
    """A test client whose database dependency points at the in-memory database."""
    from fastapi.testclient import TestClient
    from sqlalchemy.orm import sessionmaker

    from flightdata.api.main import create_app
    from flightdata.db import get_session

    factory = sessionmaker(bind=engine, expire_on_commit=False)

    def override_get_session():
        with factory() as session:
            yield session

    app = create_app()
    app.dependency_overrides[get_session] = override_get_session
    return TestClient(app)


@pytest.fixture
def make_record():
    """Factory for StateRecord objects with sensible defaults (an aircraft over Frankfurt)."""
    from flightdata.opensky_parser import StateRecord

    def _make(**overrides):
        now = datetime.now(UTC).replace(microsecond=0)
        values = {
            "icao24": "3c6444",
            "callsign": "DLH123",
            "origin_country": "Germany",
            "observed_at": now,
            "time_position": now,
            "last_contact": now,
            "longitude": 8.5,
            "latitude": 50.0,
            "baro_altitude": 10000.0,
            "geo_altitude": 10100.0,
            "velocity": 230.0,
            "true_track": 90.0,
            "vertical_rate": 0.0,
            "on_ground": False,
            "squawk": "1000",
            "spi": False,
            "position_source": 0,
        }
        values.update(overrides)
        return StateRecord(**values)

    return _make
