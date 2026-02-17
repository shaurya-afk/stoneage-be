import logging
import os
from contextlib import contextmanager
from typing import Generator, Optional
from urllib.parse import quote_plus

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from .models import Base

logger = logging.getLogger(__name__)


def _build_database_url() -> Optional[str]:
    """Build DATABASE_URL from env. Supports DATABASE_URL or separate DB_* vars (avoids password encoding issues)."""
    url = os.getenv("DATABASE_URL")
    if url:
        return url
    host = os.getenv("DB_HOST")
    port = os.getenv("DB_PORT", "5432")
    user = os.getenv("DB_USER", "postgres")
    password = os.getenv("DB_PASSWORD")
    name = os.getenv("DB_NAME", "postgres")
    if not host or not password:
        return None
    password_encoded = quote_plus(password)
    return f"postgresql://{user}:{password_encoded}@{host}:{port}/{name}"


def _ensure_ssl(url: str) -> str:
    """Supabase (and most cloud Postgres) require SSL. Append sslmode=require if not present."""
    if "sslmode=" in url:
        return url
    sep = "&" if "?" in url else "?"
    return f"{url}{sep}sslmode=require"


DATABASE_URL = _build_database_url()

_engine = None
_SessionLocal = None


def get_engine():
    global _engine
    if _engine is None and DATABASE_URL:
        url = _ensure_ssl(DATABASE_URL)
        _engine = create_engine(
            url,
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=10,
        )
        # Create tables if they don't exist
        try:
            Base.metadata.create_all(bind=_engine)
        except Exception as e:
            logger.warning("Could not create tables (they may already exist): %s", e)
    return _engine


def get_session_factory():
    global _SessionLocal
    if _SessionLocal is None:
        engine = get_engine()
        if engine:
            _SessionLocal = sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=engine,
            )
    return _SessionLocal


def is_configured() -> bool:
    return bool(DATABASE_URL)


@contextmanager
def get_db() -> Generator[Optional[Session], None, None]:
    """Context manager for database sessions. Yields None if DB is not configured."""
    SessionLocal = get_session_factory()
    if not SessionLocal:
        yield None
        return
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
