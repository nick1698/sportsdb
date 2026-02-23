import logging

from fastapi import FastAPI

from app.settings import settings
from app.logging_config import setup_logging

setup_logging(settings.log_level)
logger = logging.getLogger(__name__)

app = FastAPI(title=settings.app_name)


@app.get("/health")
def health():
    """
    Simple health endpoint.

    We avoid returning sensitive values (like DATABASE_URL content).
    We only expose whether DB config is present.
    """
    return {
        "status": "ok",
        "db_configured": settings.database_url is not None and settings.database_url != "",
    }
