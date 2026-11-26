"""Thin HTTP client for the OpenSky REST API."""

import time
from types import TracebackType
from typing import Any

import httpx

from .geo import BoundingBox


class OpenSkyError(Exception):
    """Base class for OpenSky client errors."""


class RateLimitedError(OpenSkyError):
    """HTTP 429: the credit/rate limit is used up."""

    def __init__(self, retry_after: float | None = None) -> None:
        super().__init__("OpenSky rate limit reached")
        self.retry_after = retry_after


class OpenSkyClient:
    """Fetches state vectors, optionally authenticated via OAuth2 client credentials."""

    def __init__(
        self,
        base_url: str,
        token_url: str,
        client_id: str | None = None,
        client_secret: str | None = None,
        timeout: float = 20.0,
        http: httpx.Client | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._token_url = token_url
        self._client_id = client_id
        self._client_secret = client_secret
        self._http = http or httpx.Client(timeout=timeout)
        self._token: str | None = None
        self._token_expires_at = 0.0  # time.monotonic() value

    def _auth_headers(self) -> dict[str, str]:
        if not (self._client_id and self._client_secret):
            return {}  # anonymous access
        # Refresh a minute early so a token never expires mid-request.
        if self._token is None or time.monotonic() >= self._token_expires_at - 60:
            self._refresh_token()
        return {"Authorization": f"Bearer {self._token}"}

    def _refresh_token(self) -> None:
        response = self._http.post(
            self._token_url,
            data={
                "grant_type": "client_credentials",
                "client_id": self._client_id,
                "client_secret": self._client_secret,
            },
        )
        response.raise_for_status()
        body = response.json()
        self._token = body["access_token"]
        self._token_expires_at = time.monotonic() + float(body.get("expires_in", 1800))

    def fetch_states(self, bbox: BoundingBox | None = None) -> dict[str, Any]:
        """GET /states/all, optionally restricted to a bounding box."""
        params = bbox.as_params() if bbox else {}
        response = self._http.get(
            f"{self._base_url}/states/all", params=params, headers=self._auth_headers()
        )
        if response.status_code == 429:
            retry_after = response.headers.get("X-Rate-Limit-Retry-After-Seconds")
            raise RateLimitedError(float(retry_after) if retry_after else None)
        response.raise_for_status()
        return response.json()

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> "OpenSkyClient":
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.close()
