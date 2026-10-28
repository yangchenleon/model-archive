"""Pytest fixtures that run against the dev database without leaving rows behind.

Every test gets a session bound to an outer transaction that is rolled back at
the end, so the suite can hit the real PostgreSQL while the data stays clean.
"""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.db import get_session
from app.main import app

# The dev database is published on 15432; inside docker compose it is `db:5432`.
DEFAULT_URL = "postgresql+psycopg://model_archive:model_archive_dev@localhost:15432/model_archive"
DATABASE_URL = os.getenv("TEST_DATABASE_URL", DEFAULT_URL)


@pytest.fixture(scope="session")
def engine():
    engine = create_engine(DATABASE_URL, future=True)
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    yield engine
    engine.dispose()


@pytest.fixture(scope="session", autouse=True)
def no_pollution(engine):
    """Canary: the suite must not move the row counts of the dev database."""
    tables = ("products", "assets", "tags", "asset_state_changes", "collections", "collection_items")

    def counts():
        with engine.connect() as connection:
            return tuple(connection.scalar(text(f"SELECT count(*) FROM {table}")) for table in tables)

    before = counts()
    yield
    after = counts()
    assert before == after, f"测试污染了数据库：{before} -> {after}"


@pytest.fixture
def db(engine):
    connection = engine.connect()
    outer = connection.begin()
    # Commits inside the endpoint become savepoint releases, so the outer
    # rollback still discards everything.
    session = Session(bind=connection, join_transaction_mode="create_savepoint")
    try:
        yield session
    finally:
        session.close()
        outer.rollback()
        connection.close()


@pytest.fixture
def client(db):
    def override():
        yield db

    app.dependency_overrides[get_session] = override
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def product(client):
    response = client.post(
        "/api/v1/products",
        json={"kit_name": "测试用机体", "manufacturer": "测试厂", "source": "pytest"},
    )
    assert response.status_code == 201, response.text
    return response.json()
