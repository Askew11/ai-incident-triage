import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.models.incident import Base

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./incidents.db")

# check_same_thread=False is SQLite-specific and harmless on Postgres
_connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=_connect_args)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def init_db():
    Base.metadata.create_all(bind=engine)


def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
