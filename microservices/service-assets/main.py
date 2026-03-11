from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
from shared.database import engine, Base
from assets import router as asset_router

app = FastAPI(title="Cortex AI - Assets Service")

app.include_router(asset_router)

@app.get("/")
def read_root():
    return {"message": "Assets Service Online"}
