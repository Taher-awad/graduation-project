from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
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
    Base.metadata.create_all(bind=engine)
    yield

app = FastAPI(title="Cortex AI - Rooms Service", lifespan=lifespan)

# Allow Traefik/Nginx Gateway to forward requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(room_router)

@app.get("/")
def read_root():
    return {"message": "Rooms Service Online"}
