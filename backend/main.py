from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import engine, Base, SessionLocal
from routers import auth, assets
from models import User
from auth_utils import get_password_hash

# Create Database Tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Cortex AI 3D Pipeline")

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

@app.on_event("startup")
def startup_event():
    # Seed Data
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == "taher").first()
        if not user:
            print("Seeding default user: taher")
            hashed_pw = get_password_hash("123")
            new_user = User(username="taher", password_hash=hashed_pw)
            db.add(new_user)
            db.commit()
    finally:
        db.close()

@app.get("/")
def read_root():
    return {"message": "Cortex AI Backend Online"}
