import logging

from fastapi import FastAPI
from sqlalchemy import text

from app.db import engine
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
        "db_configured": settings.database_url is not None
        and settings.database_url != "",
    }


@app.get("/db-check")
def db_check():
    if engine is None:
        return {"ok": False, "error": "DATABASE_URL not set"}

    try:
        with engine.connect() as conn:
            value = conn.execute(text("SELECT 1")).scalar_one()
        return {"ok": value == 1}
    except Exception as e:
        # TODO: non stampiamo stacktrace qui, lo farà il logging se serve
        return {"ok": False, "error": str(e)}
