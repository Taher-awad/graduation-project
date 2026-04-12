from fastapi import FastAPI
import sys
import os
from contextlib import asynccontextmanager

# Add parent dir to path so we can import shared
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.database import engine, Base
from rooms import router as room_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure Tables exist (They should from auth service, but good practice)
    # Ensure Tables exist (Delegated to Auth Service)
    pass
    yield

app = FastAPI(title="Cortex AI - Rooms Service", lifespan=lifespan)

# CORS is handled exclusively by the Nginx API Gateway

app.include_router(room_router)

@app.get("/")
def read_root():
    return {"message": "Rooms Service Online"}
