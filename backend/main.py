from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import engine, Base, SessionLocal
from routers import auth, assets, rooms
from auth_utils import get_password_hash

from sqlalchemy.orm import sessionmaker
from models import User, UserRole

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Create Tables
    Base.metadata.create_all(bind=engine)
    
    # 2. Seed Data
    # Create a session bound to the current engine (which might be patched by tests)
    SeedingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SeedingSession()
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

app = FastAPI(title="Cortex AI 3D Pipeline", lifespan=lifespan)

# CORS (Allow Unity/Web)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(auth.router)
app.include_router(assets.router)
app.include_router(rooms.router)

@app.get("/")
def read_root():
    return {"message": "Cortex AI Backend Online"}
