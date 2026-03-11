import asyncio
from shared.database import AsyncSessionLocal
from sqlalchemy import text

async def test_db():
    async with AsyncSessionLocal() as session:
        result = await session.execute(text("SELECT 1"))
        print(f"Async DB connection successful: {result.scalar() == 1}")

asyncio.run(test_db())