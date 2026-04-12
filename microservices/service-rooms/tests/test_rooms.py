import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import sys
import os

# Ensure we can import the microservice and shared library
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app
from shared.database import Base, get_db
from shared.models import User, UserRole
from shared.dependencies import get_current_user

SQLALCHEMY_DATABASE_URL = "sqlite:///./test_rooms.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Recreate tables afresh
Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)

# Seed Test Users
db = TestingSessionLocal()
test_teacher = User(username="test_teacher", password_hash="dummy", role=UserRole.TEACHER)
test_student = User(username="test_student", password_hash="dummy", role=UserRole.STUDENT)
db.add(test_teacher)
db.add(test_student)
db.commit()
db.refresh(test_teacher)
db.refresh(test_student)
db.close()

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

# Mock Authentication Dependency
def override_get_current_user_teacher():
    db = TestingSessionLocal()
    return db.query(User).filter(User.username == "test_teacher").first()

app.dependency_overrides[get_db] = override_get_db
app.dependency_overrides[get_current_user] = override_get_current_user_teacher

client = TestClient(app)

def test_create_room():
    response = client.post(
        "/rooms/",
        json={"name": "Biology 101", "description": "Cell Structure", "is_online": True}
    )
    assert response.status_code == 201
    assert response.json()["name"] == "Biology 101"
    
    global created_room_id 
    created_room_id = response.json()["id"]

def test_invite_student_to_room():
    response = client.post(
        f"/rooms/{created_room_id}/invite",
        json={"username": "test_student", "permissions": {"can_slice": True}}
    )
    assert response.status_code == 200
    assert response.json() == {"message": "Invitation sent to test_student"}

def test_student_joins_room():
    # Swap dependency to mock student
    def override_get_current_user_student():
        db = TestingSessionLocal()
        return db.query(User).filter(User.username == "test_student").first()
    
    app.dependency_overrides[get_current_user] = override_get_current_user_student

    response = client.post(f"/rooms/{created_room_id}/join")
    assert response.status_code == 200
    assert response.json() == {"message": "You have joined the room"}
