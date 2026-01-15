import asyncio
import os
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

# Use same URL logic as database.py
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./urbanous.db")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+asyncpg://", 1)
elif DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

async def migrate():
    print(f"Connecting to {DATABASE_URL}...")
    engine = create_async_engine(DATABASE_URL)
    
    async with engine.begin() as conn:
        print("Checking schema for 'news_digests'...")
        
        # 1. Check is_public
        try:
            await conn.execute(text("SELECT is_public FROM news_digests LIMIT 1"))
            print(" - Column 'is_public' exists.")
        except Exception:
            print(" - Adding column 'is_public'...")
            # SQLite vs Postgres syntax diffs handled loosely or assume Postgres given the error
            try:
                await conn.execute(text("ALTER TABLE news_digests ADD COLUMN is_public BOOLEAN DEFAULT FALSE"))
            except Exception as e:
                print(f"   Failed (might be SQLite syntax): {e}")

        # 2. Check public_slug
        try:
            await conn.execute(text("SELECT public_slug FROM news_digests LIMIT 1"))
            print(" - Column 'public_slug' exists.")
        except Exception:
            print(" - Adding column 'public_slug'...")
            try:
                await conn.execute(text("ALTER TABLE news_digests ADD COLUMN public_slug VARCHAR"))
                await conn.execute(text("CREATE INDEX ix_news_digests_public_slug ON news_digests (public_slug)"))
            except Exception as e:
                print(f"   Failed: {e}")

        # 3. Check created_at (just in case)
        try:
            await conn.execute(text("SELECT created_at FROM news_digests LIMIT 1"))
            print(" - Column 'created_at' exists.")
        except Exception:
            print(" - Adding column 'created_at'...")
            try:
                await conn.execute(text("ALTER TABLE news_digests ADD COLUMN created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()"))
            except Exception as e:
                print(f"   Failed: {e}")

    print("Migration Check Complete.")
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(migrate())
