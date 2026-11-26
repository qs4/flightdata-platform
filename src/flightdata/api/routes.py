"""API endpoints. Routes only validate input and delegate to `storage`."""

from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy.orm import Session

from .. import storage
from ..db import get_session
from ..geo import BoundingBox
from .schemas import StateVectorOut

router = APIRouter()

SessionDep = Annotated[Session, Depends(get_session)]


def bbox_params(
    lamin: Annotated[float | None, Query(ge=-90, le=90, description="Min latitude")] = None,
    lomin: Annotated[float | None, Query(ge=-180, le=180, description="Min longitude")] = None,
    lamax: Annotated[float | None, Query(ge=-90, le=90, description="Max latitude")] = None,
    lomax: Annotated[float | None, Query(ge=-180, le=180, description="Max longitude")] = None,
) -> BoundingBox | None:
    """Optional bounding box: either all four parameters or none."""
    values = (lamin, lomin, lamax, lomax)
    if all(value is None for value in values):
        return None
    if any(value is None for value in values):
        raise HTTPException(
            status_code=422,
            detail="A bounding box needs all four parameters: lamin, lomin, lamax, lomax",
        )
    try:
        return BoundingBox(lamin, lomin, lamax, lomax)  # type: ignore[arg-type]
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/health", tags=["meta"])
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/states/latest", response_model=list[StateVectorOut], tags=["states"])
def latest_states(
    session: SessionDep,
    bbox: Annotated[BoundingBox | None, Depends(bbox_params)],
    max_age_minutes: Annotated[
        int, Query(ge=1, le=1440, description="Ignore aircraft not seen within this window")
    ] = 10,
    limit: Annotated[int, Query(ge=1, le=5000)] = 500,
):
    """Newest known position per aircraft, optionally inside a bounding box."""
    return storage.latest_states(
        session, bbox=bbox, max_age=timedelta(minutes=max_age_minutes), limit=limit
    )


@router.get("/aircraft/{icao24}/track", response_model=list[StateVectorOut], tags=["aircraft"])
def aircraft_track(
    icao24: Annotated[str, Path(pattern=r"^[0-9a-fA-F]{6}$", description="6 hex characters")],
    session: SessionDep,
    since: Annotated[
        datetime | None, Query(description="Only positions at or after this time (ISO 8601)")
    ] = None,
    limit: Annotated[int, Query(ge=1, le=5000)] = 1000,
):
    """Chronological track of one aircraft (the newest `limit` points)."""
    if since is not None and since.tzinfo is None:
        since = since.replace(tzinfo=UTC)  # treat timestamps without a timezone as UTC

    points = storage.track(session, icao24, since=since, limit=limit)
    if not points:
        raise HTTPException(status_code=404, detail="No positions found for this aircraft")
    return points
