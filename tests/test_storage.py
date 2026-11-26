from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select

from flightdata.geo import BoundingBox
from flightdata.models import StateVector
from flightdata.storage import latest_states, store_states, track


def count_rows(session) -> int:
    return session.scalar(select(func.count()).select_from(StateVector))


def test_store_states_inserts_new_records(session, make_record):
    records = [make_record(icao24="aaaaaa"), make_record(icao24="bbbbbb")]

    assert store_states(session, records) == 2
    assert count_rows(session) == 2


def test_store_states_skips_duplicates(session, make_record):
    record = make_record()

    assert store_states(session, [record]) == 1
    assert store_states(session, [record]) == 0
    assert count_rows(session) == 1


def test_store_states_with_empty_list_does_nothing(session):
    assert store_states(session, []) == 0


def test_timestamps_come_back_as_utc(session, make_record):
    record = make_record()
    store_states(session, [record])

    stored = session.scalar(select(StateVector))

    assert stored.time_position == record.time_position
    assert stored.time_position.tzinfo is not None


def test_latest_states_returns_newest_position_per_aircraft(session, make_record):
    now = datetime.now(UTC).replace(microsecond=0)
    store_states(
        session,
        [
            make_record(time_position=now - timedelta(minutes=2), latitude=50.0),
            make_record(time_position=now, latitude=51.0),
        ],
    )

    result = latest_states(session, bbox=None, max_age=timedelta(minutes=10), limit=100)

    assert len(result) == 1
    assert result[0].latitude == 51.0


def test_latest_states_ignores_stale_aircraft(session, make_record):
    now = datetime.now(UTC).replace(microsecond=0)
    store_states(
        session,
        [
            make_record(icao24="aaaaaa", time_position=now),
            make_record(icao24="bbbbbb", time_position=now - timedelta(minutes=30)),
        ],
    )

    result = latest_states(session, bbox=None, max_age=timedelta(minutes=10), limit=100)

    assert [r.icao24 for r in result] == ["aaaaaa"]


def test_latest_states_filters_by_bounding_box(session, make_record):
    store_states(
        session,
        [
            make_record(icao24="aaaaaa", longitude=8.5, latitude=50.0),  # Frankfurt area
            make_record(icao24="bbbbbb", longitude=13.4, latitude=52.5),  # Berlin area
        ],
    )
    frankfurt_box = BoundingBox(lamin=49.0, lomin=7.0, lamax=51.0, lomax=9.0)

    result = latest_states(session, bbox=frankfurt_box, max_age=timedelta(minutes=10), limit=100)

    assert [r.icao24 for r in result] == ["aaaaaa"]


def test_track_is_chronological_and_limited_to_newest_points(session, make_record):
    now = datetime.now(UTC).replace(microsecond=0)
    store_states(
        session,
        [make_record(time_position=now - timedelta(minutes=m)) for m in (3, 2, 1, 0)],
    )

    points = track(session, "3C6444", since=None, limit=3)  # upper case input is accepted

    times = [p.time_position for p in points]
    assert times == sorted(times)
    assert len(points) == 3
    assert times[-1] == now


def test_track_since_filters_older_points(session, make_record):
    now = datetime.now(UTC).replace(microsecond=0)
    store_states(
        session,
        [make_record(time_position=now - timedelta(minutes=m)) for m in (10, 1)],
    )

    points = track(session, "3c6444", since=now - timedelta(minutes=5), limit=100)

    assert len(points) == 1
