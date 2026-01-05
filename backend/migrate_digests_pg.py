
import asyncio
import asyncpg
import os

# Hardcoded for safety/simplicity as importing from database.py might trigger other imports
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@localhost/memex")

async def migrate():
    print(f"Connecting to {DATABASE_URL}...")
    try:
        conn = await asyncpg.connect(DATABASE_URL)
    except Exception as e:
        print(f"Connection failed: {e}")
        return

    try:
        print("Checking 'news_digests' table...")
        # Add columns if not exist
        # asyncpg doesn't have "ADD COLUMN IF NOT EXISTS" in older postgres versions, 
        # but modern ones do. Or we can catch duplicate column error.
        
        try:
            await conn.execute("ALTER TABLE news_digests ADD COLUMN analysis_source TEXT")
            print("Added 'analysis_source'.")
        except asyncpg.exceptions.DuplicateColumnError:
            print("'analysis_source' already exists.")
        except Exception as e:
            print(f"Error adding 'analysis_source': {e}")

        try:
            await conn.execute("ALTER TABLE news_digests ADD COLUMN analysis_digest TEXT")
            print("Added 'analysis_digest'.")
        except asyncpg.exceptions.DuplicateColumnError:
            print("'analysis_digest' already exists.")
        except Exception as e:
            print(f"Error adding 'analysis_digest': {e}")
            
    finally:
        await conn.close()
    print("Migration complete.")

if __name__ == "__main__":
    asyncio.run(migrate())
