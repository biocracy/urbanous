import asyncio
from sqlalchemy import text
from database import engine

async def migrate():
    async with engine.begin() as conn:
        print("Migrating: Adding 'type' column to 'news_outlets'...")
        try:
            await conn.execute(text("ALTER TABLE news_outlets ADD COLUMN type VARCHAR DEFAULT 'Unknown';"))
            print("Migration successful: Added 'type' column.")
        except Exception as e:
            if "already exists" in str(e):
                print("Column 'type' already exists. Skipping.")
            else:
                print(f"Migration failed: {e}")

if __name__ == "__main__":
    asyncio.run(migrate())
