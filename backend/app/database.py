"""SQLAlchemy engine, session factory and declarative base."""
import logging
import time

from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import settings

logger = logging.getLogger("campusbite.db")

_is_sqlite = settings.database_url.startswith("sqlite")

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    connect_args={"check_same_thread": False} if _is_sqlite else {},
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    """FastAPI dependency that yields a DB session and always closes it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def wait_for_db(retries: int = 20, delay: float = 2.0) -> None:
    """Block until the database accepts connections (useful when Postgres boots slowly in Docker)."""
    for attempt in range(1, retries + 1):
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return
        except OperationalError:
            logger.warning("Database not ready (attempt %s/%s), retrying in %ss", attempt, retries, delay)
            time.sleep(delay)
    raise RuntimeError("Database is not reachable. Check DATABASE_URL.")


def init_db() -> None:
    from . import models  # noqa: F401  (registers models on Base.metadata)

    wait_for_db()
    Base.metadata.create_all(bind=engine)
