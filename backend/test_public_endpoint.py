import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
from models import NewsDigest
from routers.outlets import get_public_digest
# Hardcoded DB
DB_PATH = "/Users/dinu/Projects/Urbanous/backend/urbanous.db"
DATABASE_URL = f"sqlite+aiosqlite:///{DB_PATH}"

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def test_endpoint():
    print("DEBUG: Testing public endpoint logic...")
    slug = "ccgeh6vl" 
    
    async with AsyncSessionLocal() as db:
        try:
            # Manually query first to confirm DB state
            stmt = select(NewsDigest).where(NewsDigest.public_slug == slug)
            res = await db.execute(stmt)
            d = res.scalars().first()
            if d:
                print(f"DB CHECK: Found {d.title}, Public={d.is_public}, Slug='{d.public_slug}'")
            else:
                print(f"DB CHECK: Slug {slug} not found in DB")

            # Call the ACTUAL function logic (simulated)
            # We can't easily call the route function because of Depends, so we replicate the logic exactly
            print("--- Mimicking Route Logic ---")
            stmt2 = select(NewsDigest).where(NewsDigest.public_slug == slug)
            res2 = await db.execute(stmt2)
            digest = res2.scalars().first()
            
            if not digest:
                print("ROUTE CHECK: 404 - Not Found in DB")
            elif not digest.is_public:
                print("ROUTE CHECK: 404 - Not Public")
            else:
                print("ROUTE CHECK: 200 - OK")

        except Exception as e:
            print(f"CRITICAL ERROR: {e}")

if __name__ == "__main__":
    asyncio.run(test_endpoint())
