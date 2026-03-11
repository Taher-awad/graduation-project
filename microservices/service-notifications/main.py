import asyncio
import os
import json
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse
import redis.asyncio as redis

app = FastAPI(title="Cortex AI - Notifications Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")

async def get_redis_client():
    return redis.from_url(REDIS_URL)

@app.get("/notifications/stream/{client_id}")
async def message_stream(request: Request, client_id: str):
    """
    Streams events securely via Server-Sent Events (SSE) to the frontend.
    The frontend provides a client_id (usually the user's UUID).
    """
    redis_client = await get_redis_client()
    pubsub = redis_client.pubsub()
    
    # Subscribe to a specific channel for this user
    channel_name = f"user_notifications:{client_id}"
    await pubsub.subscribe(channel_name)

    async def event_generator():
        try:
            while True:
                # If client disconnects, stop sending events
                if await request.is_disconnected():
                    break

                # Non-blocking read from redis pub/sub
                message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                
                if message:
                    yield {
                        "event": "message",
                        "data": message["data"].decode("utf-8")
                    }
                
                # Small sleep to yield control to event loop
                await asyncio.sleep(0.1)
                
        except asyncio.CancelledError:
            pass
        finally:
            await pubsub.unsubscribe(channel_name)
            await redis_client.aclose()

    return EventSourceResponse(event_generator())

@app.get("/")
def read_root():
    return {"message": "Notifications Service Online"}
