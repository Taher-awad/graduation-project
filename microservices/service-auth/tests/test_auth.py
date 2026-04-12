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

SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Recreate tables afresh
Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

def test_register_staff():
    response = client.post(
        "/auth/register",
        json={"username": "test_teacher", "password": "123", "role": "TEACHER"}
    )
    assert response.status_code == 201
    assert response.json() == {"message": "User created successfully"}

def test_register_student():
    response = client.post(
        "/auth/register",
        json={"username": "test_student", "password": "123", "role": "STUDENT"}
    )
    assert response.status_code == 201

def test_register_duplicate_user():
    response = client.post(
        "/auth/register",
        json={"username": "test_student", "password": "321", "role": "STUDENT"}
    )
    assert response.status_code == 400
    assert response.json() == {"detail": "Username already registered"}

def test_login_success():
    response = client.post(
        "/auth/login",
        json={"username": "test_teacher", "password": "123", "role": "TEACHER"}
    )
    assert response.status_code == 200
    assert "access_token" in response.json()
    assert response.json()["role"] == "TEACHER"

def test_login_failure():
    response = client.post(
        "/auth/login",
        json={"username": "test_teacher", "password": "wrongpassword", "role": "TEACHER"}
    )
    assert response.status_code == 401
    assert response.json() == {"detail": "Incorrect username or password"}
