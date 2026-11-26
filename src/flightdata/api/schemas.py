"""Response models. They define what the API returns and what shows up in /docs."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class StateVectorOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    icao24: str = Field(description="ICAO 24-bit transponder address, 6 hex characters")
    callsign: str | None = Field(None, description="Callsign, e.g. DLH123")
    origin_country: str | None = Field(None, description="Country of registration")
    time_position: datetime = Field(description="Time of the position fix (UTC)")
    last_contact: datetime | None = Field(None, description="Last signal received (UTC)")
    longitude: float = Field(description="WGS84 longitude in degrees")
    latitude: float = Field(description="WGS84 latitude in degrees")
    baro_altitude: float | None = Field(None, description="Barometric altitude in metres")
    geo_altitude: float | None = Field(None, description="Geometric (GNSS) altitude in metres")
    velocity: float | None = Field(None, description="Ground speed in m/s")
    true_track: float | None = Field(None, description="Track angle, degrees clockwise from north")
    vertical_rate: float | None = Field(None, description="Climb(+)/descent(-) rate in m/s")
    on_ground: bool = Field(description="True if the aircraft reports being on the ground")
    squawk: str | None = Field(None, description="Transponder code")
