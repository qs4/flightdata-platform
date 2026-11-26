"""FastAPI application. Run with: uvicorn flightdata.api.main:app --reload"""

from fastapi import FastAPI

from .. import __version__
from .routes import router


def create_app() -> FastAPI:
    app = FastAPI(
        title="Flightdata Platform",
        version=__version__,
        description="ADS-B state vectors collected from the OpenSky Network.",
    )
    app.include_router(router)
    return app


app = create_app()
