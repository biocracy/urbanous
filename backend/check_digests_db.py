import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from models import NewsDigest, User
from sqlalchemy import select, func

# Hardcoded ABSOLUTE path to ensure we hit the real DB
DB_PATH = "/Users/dinu/Projects/Urbanous/backend/urbanous.db"
DATABASE_URL = f"sqlite+aiosqlite:///{DB_PATH}"

print(f"DEBUG: Connecting to {DATABASE_URL}")

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def check_db():
    if not os.path.exists(DB_PATH):
        print(f"ERROR: DB File not found at {DB_PATH}")
        return

    async with AsyncSessionLocal() as db:
        print("DEBUG: Checking Database...")
        
        try:
            # Check Users
            result = await db.execute(select(User))
            users = result.scalars().all()
            print(f"DEBUG: Found {len(users)} users.")
            for u in users:
                print(f" - User: {u.username} (ID: {u.id})")
                
            # Check Digests
            result = await db.execute(select(func.count(NewsDigest.id)))
            count = result.scalar()
            print(f"DEBUG: Total Digests in DB: {count}")
            
            if count > 0:
                result = await db.execute(select(NewsDigest).order_by(NewsDigest.created_at.desc()).limit(1))
                last = result.scalar()
                print(f"DEBUG: Most Recent: '{last.title}' (ID: {last.id}) Slug: {last.public_slug} Public: {last.is_public}")
                
        except Exception as e:
            print(f"ERROR: Query failed: {e}")

if __name__ == "__main__":
    asyncio.run(check_db())
