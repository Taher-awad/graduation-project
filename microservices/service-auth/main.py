from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from shared.database import engine, Base, AsyncSessionLocal
from shared.models import User, UserRole
from shared.models import User, UserRole
from auth import router as auth_router
from shared.auth_utils import get_password_hash
import os

app = FastAPI(title="Cortex AI - Auth Service")

app.include_router(auth_router)

@app.get("/")
def read_root():
    return {"message": "Auth Service Online"}
