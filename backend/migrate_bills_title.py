import asyncio
import asyncpg

DATABASE_URL = "postgresql://user:password@localhost/memex"

async def migrate():
    print("Connecting to DB...")
    try:
        conn = await asyncpg.connect(DATABASE_URL)
        print("Connected.")
        
        # Add title column
        query = "ALTER TABLE bills ADD COLUMN IF NOT EXISTS title VARCHAR;"
        
        print(f"Executing: {query}")
        await conn.execute(query)
            
        print("Migration complete.")
        await conn.close()
    except Exception as e:
        print(f"Migration failed: {e}")

if __name__ == "__main__":
    asyncio.run(migrate())
