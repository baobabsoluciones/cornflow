import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Set testing environment before importing app
os.environ["CORNFLOW_ENV"] = "testing"

from cornflow_f.database import Base, get_db
from cornflow_f.main import app
from cornflow_f.config import get_config

# Get testing configuration
config = get_config()

# Create test database using configuration
engine = create_engine(
    config.DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(
    autocommit=False, autoflush=False, bind=engine, expire_on_commit=False
)


@pytest.fixture(scope="function")
def db_session():
    """
    Create a fresh database session for each test
    """
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session):
    """
    Create a test client with a fresh database session
    """

    def override_get_db():
        try:
            yield db_session
        finally:
            db_session.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
