import asyncio
import os
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from main import Bill

# Database Setup
DATABASE_URL = "postgresql+asyncpg://user:password@localhost/memex"
engine = create_async_engine(DATABASE_URL, echo=True)
AsyncSessionLocal = sessionmaker(
    bind=engine, class_=AsyncSession, expire_on_commit=False
)

async def migrate_titles():
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Bill))
        bills = result.scalars().all()
        
        print(f"Found {len(bills)} bills. Standardizing titles...")
        
        updated_count = 0
        
        for bill in bills:
            # We need Shop Name and Date to construct the title
            if not bill.shop_name or not bill.date_str:
                print(f"Skipping Bill {bill.id}: Missing shop or date.")
                continue
            
            # Construct standard title
            new_title = f"{bill.shop_name} - {bill.date_str}"
            
            if bill.title != new_title:
                print(f"Updating Bill {bill.id}: '{bill.title}' -> '{new_title}'")
                bill.title = new_title
                updated_count += 1
            else:
                # Already correct
                pass

        if updated_count > 0:
            await session.commit()
            print(f"Migration Complete. Updated {updated_count} titles.")
        else:
            print("No titles needed updating.")

if __name__ == "__main__":
    asyncio.run(migrate_titles())
