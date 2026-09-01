"""
Shared pytest fixtures.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture()
def client() -> TestClient:
    """FastAPI TestClient for integration tests."""
    return TestClient(app)

from app.db.session import SessionLocal

@pytest.fixture(scope="function")
def db():
    """Provides a database session."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
