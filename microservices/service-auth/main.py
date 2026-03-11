from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from shared.database import engine, Base, SessionLocal
from shared.models import User, UserRole
from shared.models import User, UserRole
from auth import router as auth_router
from shared.auth_utils import get_password_hash
import sys
import os

from contextlib import asynccontextmanager

# Add parent dir to path so we can import shared
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Create Tables
    Base.metadata.create_all(bind=engine)
    
    # 2. Seed Data
    db = SessionLocal()
    try:
        # Staff User
        user = db.query(User).filter(User.username == "taher").first()
        if not user:
            print("Seeding default STAFF: taher")
            hashed_pw = get_password_hash("123")
            new_user = User(username="taher", password_hash=hashed_pw, role=UserRole.STAFF)
            db.add(new_user)
            db.commit()
            
        # Student User
        student = db.query(User).filter(User.username == "student1").first()
        if not student:
            print("Seeding default STUDENT: student1")
            hashed_pw = get_password_hash("123")
            new_student = User(username="student1", password_hash=hashed_pw, role=UserRole.STUDENT)
            db.add(new_student)
            db.commit()
    except Exception as e:
        print(f"Seeding skipped or failed: {e}")
    finally:
        db.close()
        
    yield

app = FastAPI(title="Cortex AI - Auth Service", lifespan=lifespan)

# Allow Traefik/Nginx Gateway to forward requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)

@app.get("/")
def read_root():
    return {"message": "Auth Service Online"}
