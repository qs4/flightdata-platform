"""Ingestion service: poll OpenSky, parse, store.

    python -m flightdata.ingest          # poll forever
    python -m flightdata.ingest --once   # fetch once and exit
"""

import argparse
import logging
import signal
import threading
from collections.abc import Callable
from dataclasses import dataclass

import httpx
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from .config import get_settings
from .db import get_sessionmaker
from .geo import BoundingBox
from .opensky_client import OpenSkyClient, OpenSkyError, RateLimitedError
from .opensky_parser import parse_states
from .storage import store_states

logger = logging.getLogger("flightdata.ingest")

SessionFactory = Callable[[], Session]


@dataclass(frozen=True)
class IngestStats:
    received: int  # rows OpenSky sent
    skipped: int  # rows dropped by the parser
    inserted: int  # rows that were new to the database


def run_once(
    client: OpenSkyClient, session_factory: SessionFactory, bbox: BoundingBox
) -> IngestStats:
    payload = client.fetch_states(bbox)
    parsed = parse_states(payload)
    with session_factory() as session:
        inserted = store_states(session, parsed.records)
    return IngestStats(
        received=len(parsed.records) + parsed.skipped,
        skipped=parsed.skipped,
        inserted=inserted,
    )


def run_forever(
    client: OpenSkyClient,
    session_factory: SessionFactory,
    bbox: BoundingBox,
    interval: float,
    stop: threading.Event,
) -> None:
    while not stop.is_set():
        wait = interval
        try:
            stats = run_once(client, session_factory, bbox)
            logger.info(
                "received=%d skipped=%d inserted=%d",
                stats.received,
                stats.skipped,
                stats.inserted,
            )
        except RateLimitedError as exc:
            wait = max(interval, exc.retry_after or 0)
            logger.warning("Rate limit reached, waiting %.0f s", wait)
        except (OpenSkyError, httpx.HTTPError, SQLAlchemyError, ValueError) as exc:
            # One bad poll must not stop the service; log it and try again next round.
            logger.error("Poll failed: %s: %s", type(exc).__name__, exc)
        stop.wait(wait)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Poll OpenSky and store state vectors.")
    parser.add_argument("--once", action="store_true", help="fetch once and exit")
    parser.add_argument(
        "--interval", type=int, default=None, help="seconds between polls (default: from settings)"
    )
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )

    settings = get_settings()
    interval = args.interval or settings.ingest_interval_seconds

    stop = threading.Event()
    signal.signal(signal.SIGINT, lambda *_: stop.set())
    signal.signal(signal.SIGTERM, lambda *_: stop.set())

    with OpenSkyClient(
        base_url=settings.opensky_base_url,
        token_url=settings.opensky_token_url,
        client_id=settings.opensky_client_id,
        client_secret=settings.opensky_client_secret,
    ) as client:
        session_factory = get_sessionmaker()
        if args.once:
            stats = run_once(client, session_factory, settings.bbox)
            logger.info(
                "received=%d skipped=%d inserted=%d",
                stats.received,
                stats.skipped,
                stats.inserted,
            )
        else:
            logger.info("Polling every %d s. Stop with Ctrl+C.", interval)
            run_forever(client, session_factory, settings.bbox, interval, stop)


if __name__ == "__main__":
    main()
