import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

DATABASE_URL = "postgresql+asyncpg://user:password@localhost/memex"

async def migrate():
    engine = create_async_engine(DATABASE_URL, echo=True)
    async with engine.begin() as conn:
        print("Migrating: Adding 'loop' column to annotations table...")
        try:
            await conn.execute(text("ALTER TABLE annotations ADD COLUMN loop BOOLEAN DEFAULT FALSE"))
            print("Migration successful.")
        except Exception as e:
            print(f"Migration failed (maybe column exists?): {e}")

if __name__ == "__main__":
    asyncio.run(migrate())
