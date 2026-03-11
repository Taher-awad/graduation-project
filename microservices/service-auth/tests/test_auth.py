import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
import os

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from main import app
from shared.database import Base, get_db

SQLALCHEMY_DATABASE_URL = "sqlite+aiosqlite:///./test_auth.db"

engine = create_async_engine(SQLALCHEMY_DATABASE_URL, echo=False)
TestingSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

async def override_get_db():
    async with TestingSessionLocal() as session:
        yield session

app.dependency_overrides[get_db] = override_get_db

@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()

@pytest_asyncio.fixture
async def async_client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

@pytest.mark.asyncio
async def test_register_staff(async_client: AsyncClient):
    response = await async_client.post(
        "/auth/register",
        json={"username": "test_teacher", "password": "123", "role": "STAFF"}
    )
    assert response.status_code == 201
    assert response.json() == {"message": "User created successfully"}

@pytest.mark.asyncio
async def test_register_student(async_client: AsyncClient):
    response = await async_client.post(
        "/auth/register",
        json={"username": "test_student", "password": "123", "role": "STUDENT"}
    )
    assert response.status_code == 201

@pytest.mark.asyncio
async def test_register_duplicate_user(async_client: AsyncClient):
    response = await async_client.post(
        "/auth/register",
        json={"username": "test_student", "password": "321", "role": "STUDENT"}
    )
    assert response.status_code == 400
    assert response.json() == {"detail": "Username already registered"}

@pytest.mark.asyncio
async def test_login_success(async_client: AsyncClient):
    response = await async_client.post(
        "/auth/login",
        json={"username": "test_teacher", "password": "123", "role": "STAFF"}
    )
    assert response.status_code == 200
    assert "access_token" in response.json()
    assert response.json()["role"] == "STAFF"

@pytest.mark.asyncio
async def test_login_failure(async_client: AsyncClient):
    response = await async_client.post(
        "/auth/login",
        json={"username": "test_teacher", "password": "wrongpassword", "role": "STAFF"}
    )
    assert response.status_code == 401
    assert response.json() == {"detail": "Incorrect username or password"}
