import asyncio
from sqlalchemy import text
from database import engine

async def migrate_schema():
    async with engine.begin() as conn:
        print("Migrating: Adding 'popularity' and 'focus' columns to 'news_outlets'...")
        
        # Add 'popularity' column
        try:
            await conn.execute(text("ALTER TABLE news_outlets ADD COLUMN popularity INTEGER DEFAULT 5;"))
            print("Migration successful: Added 'popularity' column.")
        except Exception as e:
            if "already exists" in str(e) or "duplicate column" in str(e):
                print("Column 'popularity' already exists. Skipping.")
            else:
                print(f"Migration failed for 'popularity': {e}")
                
        # Add 'focus' column
        try:
            await conn.execute(text("ALTER TABLE news_outlets ADD COLUMN focus VARCHAR DEFAULT 'Local';"))
            print("Migration successful: Added 'focus' column.")
        except Exception as e:
            if "already exists" in str(e) or "duplicate column" in str(e):
                print("Column 'focus' already exists. Skipping.")
            else:
                print(f"Migration failed for 'focus': {e}")

if __name__ == "__main__":
    asyncio.run(migrate_schema())
