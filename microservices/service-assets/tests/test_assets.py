import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
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

SQLALCHEMY_DATABASE_URL = "sqlite:///./test_assets.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)

# Seed Test Teacher
db = TestingSessionLocal()
test_teacher = User(username="test_teacher", password_hash="dummy", role=UserRole.STAFF)
db.add(test_teacher)
db.commit()
db.refresh(test_teacher)
db.close()

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

def override_get_current_user_teacher():
    db = TestingSessionLocal()
    return db.query(User).filter(User.username == "test_teacher").first()

app.dependency_overrides[get_db] = override_get_db
app.dependency_overrides[get_current_user] = override_get_current_user_teacher

client = TestClient(app)

def test_upload_asset():
    # Mimic a valid .glb file upload
    file_content = b"mock glb binary data"
    files = {
        "file": ("test_model.glb", io.BytesIO(file_content), "model/gltf-binary")
    }
    data = {
        "asset_type": "MODEL",
        "is_sliceable": "True"
    }
    
    response = client.post("/assets/upload", files=files, data=data)
    
    assert response.status_code == 200
    json_resp = response.json()
    assert "id" in json_resp
    assert json_resp["type"] == "MODEL"
    assert json_resp["status"] == "PENDING"
