from datetime import UTC, datetime

import pytest

from flightdata.opensky_parser import parse_states

OBSERVED = 1_700_000_002
POSITION = 1_700_000_000


def make_row(**overrides):
    """One OpenSky state vector (17 fields). Override fields by name."""
    fields = {
        "icao24": "3C6444",
        "callsign": "DLH123  ",
        "origin_country": "Germany",
        "time_position": POSITION,
        "last_contact": POSITION + 1,
        "longitude": 8.5,
        "latitude": 50.0,
        "baro_altitude": 10000.0,
        "on_ground": False,
        "velocity": 230.0,
        "true_track": 90.0,
        "vertical_rate": 0.5,
        "sensors": None,
        "geo_altitude": 10100.0,
        "squawk": "1000",
        "spi": False,
        "position_source": 0,
    }
    fields.update(overrides)
    return list(fields.values())


def test_parses_a_valid_row():
    result = parse_states({"time": OBSERVED, "states": [make_row()]})

    assert result.skipped == 0
    assert len(result.records) == 1
    record = result.records[0]
    assert record.icao24 == "3c6444"  # normalised to lowercase
    assert record.callsign == "DLH123"  # padding removed
    assert record.origin_country == "Germany"
    assert record.time_position == datetime.fromtimestamp(POSITION, tz=UTC)
    assert record.observed_at == datetime.fromtimestamp(OBSERVED, tz=UTC)
    assert record.longitude == 8.5
    assert record.latitude == 50.0
    assert record.velocity == 230.0
    assert record.on_ground is False


def test_accepts_extended_rows_with_category():
    row = make_row() + [3]  # 18th field: category, only sent with extended=1

    result = parse_states({"time": OBSERVED, "states": [row]})

    assert len(result.records) == 1


def test_empty_callsign_becomes_none():
    result = parse_states({"time": OBSERVED, "states": [make_row(callsign="        ")]})

    assert result.records[0].callsign is None


def test_missing_optional_values_stay_none():
    row = make_row(baro_altitude=None, velocity=None, vertical_rate=None, squawk=None)

    record = parse_states({"time": OBSERVED, "states": [row]}).records[0]

    assert record.baro_altitude is None
    assert record.velocity is None
    assert record.vertical_rate is None
    assert record.squawk is None


@pytest.mark.parametrize(
    "row",
    [
        make_row(latitude=None),
        make_row(longitude=None),
        make_row(time_position=None),
        make_row(icao24=""),
        make_row()[:10],  # truncated row
    ],
    ids=["no-latitude", "no-longitude", "no-time-position", "no-icao24", "too-short"],
)
def test_skips_rows_that_cannot_be_used(row):
    result = parse_states({"time": OBSERVED, "states": [row, make_row(icao24="abcdef")]})

    assert result.skipped == 1
    assert [r.icao24 for r in result.records] == ["abcdef"]


def test_null_states_means_no_aircraft():
    result = parse_states({"time": OBSERVED, "states": None})

    assert result.records == []
    assert result.skipped == 0


def test_response_without_time_is_rejected():
    with pytest.raises(ValueError):
        parse_states({"states": []})
