import asyncio
from database import engine, Base
from models import Country, CityMetadata

async def init_db():
    async with engine.begin() as conn:
        # Drop to force update (Dev Only)
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    print("Database tables created/updated successfully.")

if __name__ == "__main__":
    asyncio.run(init_db())
