import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from app.db.models import Base

# Database path / URL configuration
SQLITE_DEFAULT_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "ott_intelligence.db"
)

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    # Ensure directory exists for local SQLite database
    os.makedirs(os.path.dirname(SQLITE_DEFAULT_PATH), exist_ok=True)
    DATABASE_URL = f"sqlite:///{SQLITE_DEFAULT_PATH}"

# Normalization for Render postgres URLs (postgres:// -> postgresql://)
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

is_sqlite = DATABASE_URL.startswith("sqlite")

connect_args = {"check_same_thread": False} if is_sqlite else {}
engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True
)

SessionLocal = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))


def init_orm_tables():
    """Creates all defined tables if they do not yet exist."""
    Base.metadata.create_all(bind=engine)


def get_db_session():
    """Dependency / context session provider."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
