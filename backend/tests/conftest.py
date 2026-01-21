import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from typing import AsyncGenerator, Generator
from fastapi.testclient import TestClient
import os
import sys

# Add backend to path so imports work
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app
from database import Base, get_db
from auth_utils import create_access_token

# Use in-memory SQLite for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, 
    connect_args={"check_same_thread": False}, 
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="session")
def db_engine():
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def db(db_engine) -> Generator:
    connection = db_engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    yield session
    session.close()
    transaction.rollback()
    connection.close()

@pytest.fixture(scope="function")
def client(db) -> Generator:
    app.dependency_overrides[get_db] = lambda: db
    # Patch the engine used in main.py lifespan to use our test engine
    # This prevents connecting to the production DB during test startup
    import main
    original_engine = main.engine
    main.engine = engine
    
    with TestClient(app) as c:
        yield c
        
    # Restore (though usually not needed if process dies, but good practice)
    main.engine = original_engine
    app.dependency_overrides.clear()

@pytest.fixture
def auth_header(client):
    # Create a test user directly or via API
    username = "testuser"
    password = "testpassword"
    client.post("/auth/register", json={"username": username, "password": password, "role": "STUDENT"})
    
    # Login to get token
    response = client.post("/auth/login", json={"username": username, "password": password})
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def staff_auth_header(client):
    # Create a staff user
    username = "staffuser"
    password = "staffpassword"
    client.post("/auth/register", json={"username": username, "password": password, "role": "STAFF"})
    
    # Login to get token
    response = client.post("/auth/login", json={"username": username, "password": password})
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
