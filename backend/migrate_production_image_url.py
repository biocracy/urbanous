
import asyncio
import asyncpg
import os
from dotenv import load_dotenv

# Load env variables including DATABASE_URL
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

async def migrate():
    if not DATABASE_URL or "postgres" not in DATABASE_URL:
        print("ERROR: DATABASE_URL not found or invalid.")
        return

    print(f"Connecting to Production DB...")
    # Hide password in logs
    safe_url = DATABASE_URL.split("@")[-1]
    print(f"Target: ...@{safe_url}")

    try:
        conn = await asyncpg.connect(DATABASE_URL)
    except Exception as e:
        print(f"Connection failed: {e}")
        return

    try:
        print("Checking 'news_digests' table for 'image_url' column...")
        
        # 1. Add Column
        try:
            await conn.execute("ALTER TABLE news_digests ADD COLUMN image_url TEXT")
            print("SUCCESS: Added 'image_url' column.")
        except asyncpg.exceptions.DuplicateColumnError:
            print("SKIPPED: 'image_url' already exists.")
        except Exception as e:
            print(f"ERROR: Failed to add column: {e}")

        # 2. Backfill Data
        placeholder_path = "/static/digest_images/placeholder.png"
        print(f"Assigning placeholder '{placeholder_path}' to existing digests...")
        
        # Update rows where image_url is NULL or empty
        result = await conn.execute(f"""
            UPDATE news_digests 
            SET image_url = '{placeholder_path}' 
            WHERE image_url IS NULL OR image_url = ''
        """)
        
        print(f"SUCCESS: Backfill complete. {result}")
            
    finally:
        await conn.close()
    print("Migration finished.")

if __name__ == "__main__":
    asyncio.run(migrate())
