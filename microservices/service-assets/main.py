from fastapi import FastAPI
import sys
import os
from contextlib import asynccontextmanager

# Add parent dir to path so we can import shared
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.database import engine, Base
from assets import router as asset_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Create Tables
    # Ensure Tables exist (Delegated to Auth Service)
    pass
    yield

app = FastAPI(title="Cortex AI - Assets Service", lifespan=lifespan)

# CORS is handled exclusively by the Nginx API Gateway

app.include_router(asset_router)

@app.get("/")
def read_root():
    return {"message": "Assets Service Online"}
