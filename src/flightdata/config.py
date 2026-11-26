"""Application settings, read from environment variables (prefix FLIGHTDATA_) or a .env file."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

from .geo import BoundingBox


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="FLIGHTDATA_", env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://flightdata:flightdata@localhost:5432/flightdata"

    opensky_base_url: str = "https://opensky-network.org/api"
    opensky_token_url: str = (
        "https://auth.opensky-network.org/auth/realms/opensky-network/protocol/openid-connect/token"
    )
    # Optional OAuth2 client credentials. Without them requests are anonymous.
    opensky_client_id: str | None = None
    opensky_client_secret: str | None = None

    ingest_interval_seconds: int = 120

    # Area that is polled. The default covers roughly Germany.
    bbox_lamin: float = 47.3
    bbox_lomin: float = 5.9
    bbox_lamax: float = 55.1
    bbox_lomax: float = 15.1

    @property
    def bbox(self) -> BoundingBox:
        return BoundingBox(self.bbox_lamin, self.bbox_lomin, self.bbox_lamax, self.bbox_lomax)


@lru_cache
def get_settings() -> Settings:
    return Settings()
