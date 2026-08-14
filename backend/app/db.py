from __future__ import annotations
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql+psycopg://model_archive:model_archive_dev@db:5432/model_archive")
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
class Base(DeclarativeBase):
    pass
def get_session():
    with SessionLocal() as session:
        yield session
