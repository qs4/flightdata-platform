"""Turn an OpenSky `/states/all` response into clean records.

This module is pure Python (no HTTP, no database) so it is easy to test.

OpenSky returns each aircraft as a JSON array with fixed positions:

    0 icao24          6 latitude        12 sensors
    1 callsign        7 baro_altitude   13 geo_altitude
    2 origin_country  8 on_ground       14 squawk
    3 time_position   9 velocity        15 spi
    4 last_contact   10 true_track      16 position_source
    5 longitude      11 vertical_rate   17 category (only with extended=1)
"""

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import IntEnum
from typing import Any

logger = logging.getLogger(__name__)


class Field(IntEnum):
    ICAO24 = 0
    CALLSIGN = 1
    ORIGIN_COUNTRY = 2
    TIME_POSITION = 3
    LAST_CONTACT = 4
    LONGITUDE = 5
    LATITUDE = 6
    BARO_ALTITUDE = 7
    ON_GROUND = 8
    VELOCITY = 9
    TRUE_TRACK = 10
    VERTICAL_RATE = 11
    SENSORS = 12
    GEO_ALTITUDE = 13
    SQUAWK = 14
    SPI = 15
    POSITION_SOURCE = 16
    CATEGORY = 17


# Rows shorter than this are malformed. The 18th field (category) is optional.
MIN_FIELDS = 17


@dataclass(frozen=True, slots=True)
class StateRecord:
    """A validated position report. Field names match the `StateVector` DB model."""

    icao24: str
    callsign: str | None
    origin_country: str | None
    observed_at: datetime
    time_position: datetime
    last_contact: datetime | None
    longitude: float
    latitude: float
    baro_altitude: float | None
    geo_altitude: float | None
    velocity: float | None
    true_track: float | None
    vertical_rate: float | None
    on_ground: bool
    squawk: str | None
    spi: bool
    position_source: int | None


@dataclass(frozen=True, slots=True)
class ParsedStates:
    records: list[StateRecord]
    skipped: int  # rows dropped because they were malformed or had no position


def _to_datetime(unix_seconds: int | float | None) -> datetime | None:
    if unix_seconds is None:
        return None
    return datetime.fromtimestamp(unix_seconds, tz=UTC)


def _to_float(value: Any) -> float | None:
    return None if value is None else float(value)


def _parse_row(row: list[Any], observed_at: datetime) -> StateRecord | None:
    if len(row) < MIN_FIELDS:
        return None

    icao24 = row[Field.ICAO24]
    time_position = row[Field.TIME_POSITION]
    longitude = row[Field.LONGITUDE]
    latitude = row[Field.LATITUDE]

    # Without an identifier, a position timestamp and a position there is nothing to store.
    if not icao24 or time_position is None or longitude is None or latitude is None:
        return None

    callsign = (row[Field.CALLSIGN] or "").strip() or None
    position_source = row[Field.POSITION_SOURCE]

    return StateRecord(
        icao24=str(icao24).lower(),
        callsign=callsign,
        origin_country=row[Field.ORIGIN_COUNTRY],
        observed_at=observed_at,
        time_position=_to_datetime(time_position),  # type: ignore[arg-type]
        last_contact=_to_datetime(row[Field.LAST_CONTACT]),
        longitude=float(longitude),
        latitude=float(latitude),
        baro_altitude=_to_float(row[Field.BARO_ALTITUDE]),
        geo_altitude=_to_float(row[Field.GEO_ALTITUDE]),
        velocity=_to_float(row[Field.VELOCITY]),
        true_track=_to_float(row[Field.TRUE_TRACK]),
        vertical_rate=_to_float(row[Field.VERTICAL_RATE]),
        on_ground=bool(row[Field.ON_GROUND]),
        squawk=row[Field.SQUAWK],
        spi=bool(row[Field.SPI]),
        position_source=None if position_source is None else int(position_source),
    )


def parse_states(payload: dict[str, Any]) -> ParsedStates:
    """Parse a decoded `/states/all` JSON response.

    OpenSky sends `"states": null` when no aircraft are visible, which yields an empty result.
    """
    if "time" not in payload:
        raise ValueError("OpenSky response has no 'time' field")

    observed_at = datetime.fromtimestamp(payload["time"], tz=UTC)
    rows = payload.get("states") or []

    records: list[StateRecord] = []
    skipped = 0
    for row in rows:
        record = _parse_row(row, observed_at)
        if record is None:
            skipped += 1
        else:
            records.append(record)

    if skipped:
        logger.debug("Skipped %d of %d rows", skipped, len(rows))
    return ParsedStates(records=records, skipped=skipped)
