from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
from shared.database import engine, Base
from rooms import router as room_router

app = FastAPI(title="Cortex AI - Rooms Service")

app.include_router(room_router)

@app.get("/")
def read_root():
    return {"message": "Rooms Service Online"}
