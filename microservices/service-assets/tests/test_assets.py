import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import sessionmaker
import sys
import os
import io

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app
from shared.database import Base, get_db
from shared.models import User, UserRole, AssetType, AssetStatus
from shared.dependencies import get_current_user

# --- Mocking strict AWS S3 calls sotests don't fail without MinIO running locally ---
import assets
class MockS3Client:
    def upload_fileobj(self, *args, **kwargs): pass
    def head_bucket(self, *args, **kwargs): pass
    def create_bucket(self, *args, **kwargs): pass
    def generate_presigned_url(self, *args, **kwargs): return "http://mock-s3-url.com"

assets.s3 = MockS3Client()
assets.s3_signer = MockS3Client()

# --- Mock Celery send_task to prevent Redis connection error during pytest ---
class MockCeleryApp:
    def send_task(self, name, args):
        print(f"Mocking Celery Task: {name} with args {args}")

assets.celery_app = MockCeleryApp()

SQLALCHEMY_DATABASE_URL = "sqlite+aiosqlite:///./test_assets.db"

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
        db.add(test_teacher)
        await db.commit()

    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()

@pytest_asyncio.fixture
async def async_client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

@pytest.mark.asyncio
async def test_upload_asset(async_client: AsyncClient):
    # Mimic a valid .glb file upload
    file_content = b"mock glb binary data"
    files = {
        "file": ("test_model.glb", io.BytesIO(file_content), "model/gltf-binary")
    }
    data = {
        "asset_type": "MODEL",
        "is_sliceable": "True"
    }
    
    response = await async_client.post("/assets/upload", files=files, data=data)
    
    assert response.status_code == 200
    json_resp = response.json()
    assert "id" in json_resp
    assert json_resp["type"] == "MODEL"
    assert json_resp["status"] == "PENDING"
