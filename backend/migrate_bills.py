import asyncio
import asyncpg

DATABASE_URL = "postgresql://user:password@localhost/memex"

async def migrate():
    print("Connecting to DB...")
    try:
        conn = await asyncpg.connect(DATABASE_URL)
        print("Connected.")
        
        # Add columns if they don't exist
        queries = [
            "ALTER TABLE bills ADD COLUMN IF NOT EXISTS shop_name VARCHAR;",
            "ALTER TABLE bills ADD COLUMN IF NOT EXISTS date_str VARCHAR;",
            "ALTER TABLE bills ADD COLUMN IF NOT EXISTS total_sum FLOAT;",
            "ALTER TABLE bills ADD COLUMN IF NOT EXISTS items VARCHAR DEFAULT '[]';",
        ]
        
        for q in queries:
            print(f"Executing: {q}")
            await conn.execute(q)
            
        print("Migration complete.")
        await conn.close()
    except Exception as e:
        print(f"Migration failed: {e}")

if __name__ == "__main__":
    asyncio.run(migrate())
