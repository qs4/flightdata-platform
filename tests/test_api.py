"""API tests. The `client` fixture talks to an in-memory SQLite database.

Note: the client is used without a `with` block on purpose, so no startup events run.
"""

from datetime import UTC, datetime, timedelta

from flightdata.storage import store_states


def test_health(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_latest_states_returns_stored_aircraft(client, session, make_record):
    store_states(session, [make_record(icao24="aaaaaa", callsign="DLH1")])

    response = client.get("/states/latest")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["icao24"] == "aaaaaa"
    assert body[0]["callsign"] == "DLH1"
    assert body[0]["latitude"] == 50.0


def test_latest_states_filters_by_bounding_box(client, session, make_record):
    store_states(
        session,
        [
            make_record(icao24="aaaaaa", longitude=8.5, latitude=50.0),
            make_record(icao24="bbbbbb", longitude=13.4, latitude=52.5),
        ],
    )

    response = client.get(
        "/states/latest", params={"lamin": 49, "lomin": 7, "lamax": 51, "lomax": 9}
    )

    assert response.status_code == 200
    assert [item["icao24"] for item in response.json()] == ["aaaaaa"]


def test_incomplete_bounding_box_is_rejected(client):
    response = client.get("/states/latest", params={"lamin": 49, "lomin": 7})

    assert response.status_code == 422


def test_inverted_bounding_box_is_rejected(client):
    response = client.get(
        "/states/latest", params={"lamin": 51, "lomin": 7, "lamax": 49, "lomax": 9}
    )

    assert response.status_code == 422


def test_track_returns_points_in_chronological_order(client, session, make_record):
    now = datetime.now(UTC).replace(microsecond=0)
    store_states(
        session,
        [make_record(time_position=now - timedelta(minutes=m)) for m in (2, 1, 0)],
    )

    response = client.get("/aircraft/3c6444/track")

    assert response.status_code == 200
    times = [point["time_position"] for point in response.json()]
    assert len(times) == 3
    assert times == sorted(times)


def test_track_for_unknown_aircraft_is_404(client):
    response = client.get("/aircraft/abcdef/track")

    assert response.status_code == 404


def test_track_with_invalid_icao24_is_422(client):
    response = client.get("/aircraft/not-hex/track")

    assert response.status_code == 422


def test_track_accepts_naive_since_timestamp(client, session, make_record):
    store_states(session, [make_record()])

    response = client.get("/aircraft/3c6444/track", params={"since": "2000-01-01T00:00:00"})

    assert response.status_code == 200
