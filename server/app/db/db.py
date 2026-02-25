from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.settings import settings

if not settings.database_url:
    # We keep this lazy: app can still start without DB configured,
    # but DB-dependent endpoints should fail clearly.
    engine = None
    LocalSession = None
else:
    engine = create_engine(settings.database_url, pool_pre_ping=True)
    LocalSession = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def get_db() -> Generator[Session, None, None]:
    if LocalSession is None:
        raise RuntimeError("DB session is unavailable: DATABASE_URL is not set")

    db: Session = LocalSession()
    try:
        yield db
    finally:
        db.close()
