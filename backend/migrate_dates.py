import asyncio
import os
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from main import Bill
from dateutil import parser
import datetime

# Database Setup (Reused from main.py)
DATABASE_URL = "postgresql+asyncpg://user:password@localhost/memex"
engine = create_async_engine(DATABASE_URL, echo=True)
AsyncSessionLocal = sessionmaker(
    bind=engine, class_=AsyncSession, expire_on_commit=False
)

async def migrate_dates():
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Bill))
        bills = result.scalars().all()
        
        print(f"Found {len(bills)} bills. Checking dates...")
        
        updated_count = 0
        
        for bill in bills:
            if not bill.date_str:
                continue
                
            original_date = bill.date_str.strip()
            
            # Skip if already in DD.MM.YYYY format
            # Simple regex check or just formatting check
            try:
                # Try to fuzzy parse the date
                dt = parser.parse(original_date, dayfirst=True)
                new_date_str = dt.strftime("%d.%m.%Y")
                
                if new_date_str != original_date:
                    print(f"Updating Bill {bill.id}: '{original_date}' -> '{new_date_str}'")
                    bill.date_str = new_date_str
                    updated_count += 1
                else:
                    # Valid format already
                    pass
                    
            except Exception as e:
                print(f"Skipping Bill {bill.id} ('{original_date}'): Could not parse. Error: {e}")

        if updated_count > 0:
            await session.commit()
            print(f"Migration Complete. Updated {updated_count} bills.")
        else:
            print("No bills needed updating.")

if __name__ == "__main__":
    asyncio.run(migrate_dates())
