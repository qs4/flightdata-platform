"""Small geographic helpers."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class BoundingBox:
    """A latitude/longitude rectangle in decimal degrees (WGS84).

    The box must not cross the antimeridian (lomin <= lomax).
    """

    lamin: float
    lomin: float
    lamax: float
    lomax: float

    def __post_init__(self) -> None:
        if not -90 <= self.lamin <= self.lamax <= 90:
            raise ValueError("Latitudes must satisfy -90 <= lamin <= lamax <= 90")
        if not -180 <= self.lomin <= self.lomax <= 180:
            raise ValueError("Longitudes must satisfy -180 <= lomin <= lomax <= 180")

    def as_params(self) -> dict[str, float]:
        """Query parameters in the form the OpenSky REST API expects."""
        return {
            "lamin": self.lamin,
            "lomin": self.lomin,
            "lamax": self.lamax,
            "lomax": self.lomax,
        }
