"""Database models."""

from datetime import UTC, datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Float,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.types import TypeDecorator


class Base(DeclarativeBase):
    pass


class UTCDateTime(TypeDecorator):
    """Timezone-aware datetimes that always come back as UTC.

    PostgreSQL stores timestamptz natively. SQLite (used in the tests) drops the timezone,
    so this decorator restores it. Naive datetimes are rejected on purpose.
    """

    impl = DateTime
    cache_ok = True

    def load_dialect_impl(self, dialect):
        return dialect.type_descriptor(DateTime(timezone=True))

    def process_bind_param(self, value: datetime | None, dialect) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError("Naive datetime is not allowed; attach a timezone (UTC).")
        return value.astimezone(UTC)

    def process_result_value(self, value: datetime | None, dialect) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)


class StateVector(Base):
    """One position report of one aircraft (an ADS-B 'state vector' from OpenSky).

    Units follow OpenSky: altitudes in metres, velocity and vertical rate in m/s,
    true_track in degrees clockwise from north.
    """

    __tablename__ = "state_vectors"
    __table_args__ = (
        # The same position can be returned by several polls; keep it only once.
        UniqueConstraint("icao24", "time_position", name="uq_state_vectors_icao24_time_position"),
        Index("ix_state_vectors_time_position", "time_position"),
    )

    # BigInteger on PostgreSQL, plain Integer on SQLite (needed for autoincrement there).
    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer(), "sqlite"), primary_key=True, autoincrement=True
    )

    icao24: Mapped[str] = mapped_column(String(6), nullable=False)
    callsign: Mapped[str | None] = mapped_column(String(8))
    origin_country: Mapped[str | None] = mapped_column(String(64))

    observed_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)
    time_position: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)
    last_contact: Mapped[datetime | None] = mapped_column(UTCDateTime)

    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    baro_altitude: Mapped[float | None] = mapped_column(Float)
    geo_altitude: Mapped[float | None] = mapped_column(Float)

    velocity: Mapped[float | None] = mapped_column(Float)
    true_track: Mapped[float | None] = mapped_column(Float)
    vertical_rate: Mapped[float | None] = mapped_column(Float)

    on_ground: Mapped[bool] = mapped_column(Boolean, nullable=False)
    squawk: Mapped[str | None] = mapped_column(String(4))
    spi: Mapped[bool] = mapped_column(Boolean, nullable=False)
    position_source: Mapped[int | None] = mapped_column(Integer)
