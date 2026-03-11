import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import sessionmaker
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from main import app
from shared.database import Base, get_db
from shared.models import User, UserRole
from shared.dependencies import get_current_user

SQLALCHEMY_DATABASE_URL = "sqlite+aiosqlite:///./test_rooms.db"

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

async def override_get_current_user_teacher():
    async with TestingSessionLocal() as session:
        result = await session.execute(select(User).filter(User.username == "test_teacher"))
        return result.scalars().first()

app.dependency_overrides[get_db] = override_get_db
app.dependency_overrides[get_current_user] = override_get_current_user_teacher

@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    async with TestingSessionLocal() as db:
        test_teacher = User(username="test_teacher", password_hash="dummy", role=UserRole.STAFF)
        test_student = User(username="test_student", password_hash="dummy", role=UserRole.STUDENT)
        db.add(test_teacher)
        db.add(test_student)
        await db.commit()

    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()

@pytest_asyncio.fixture
async def async_client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

# Using a fixture to maintain state between tests since Pytest executes tests in random order if parallelized,
# but here we rely on the specific sequential execution of these tests as defined initially.
# A cleaner way is chaining, but for minimal refactoring we mimic the original global var.
created_room_id = None

@pytest.mark.asyncio
async def test_create_room(async_client: AsyncClient):
    global created_room_id
    response = await async_client.post(
        "/rooms/",
        json={"name": "Biology 101", "description": "Cell Structure", "is_online": True}
    )
    assert response.status_code == 201
    assert response.json()["name"] == "Biology 101"
    created_room_id = response.json()["id"]

@pytest.mark.asyncio
async def test_invite_student_to_room(async_client: AsyncClient):
    response = await async_client.post(
        f"/rooms/{created_room_id}/invite",
        json={"username": "test_student", "permissions": {"can_slice": True}}
    )
    assert response.status_code == 200
    assert response.json() == {"message": "Invitation sent to test_student"}

@pytest.mark.asyncio
async def test_student_joins_room(async_client: AsyncClient):
    # Swap dependency to mock student
    async def override_get_current_user_student():
        async with TestingSessionLocal() as db:
            result = await db.execute(select(User).filter(User.username == "test_student"))
            return result.scalars().first()
    
    app.dependency_overrides[get_current_user] = override_get_current_user_student

    response = await async_client.post(f"/rooms/{created_room_id}/join")
    assert response.status_code == 200
    assert response.json() == {"message": "You have joined the room"}
