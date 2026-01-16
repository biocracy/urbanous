
import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

async def list_tables():
    if not DATABASE_URL:
        print("DATABASE_URL not found in .env")
        return

    print(f"Connecting to {DATABASE_URL.split('@')[1]}...") # Don't log password
    
    try:
        conn = await asyncpg.connect(DATABASE_URL)
        print("Connected successfully!")
        
        rows = await conn.fetch("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name;
        """)
        
        print("\n--- Tables in Railway DB ---")
        if not rows:
            print("(No tables found)")
        for row in rows:
            print(f"- {row['table_name']}")
            
            # Optional: Count rows
            try:
                count = await conn.fetchval(f"SELECT COUNT(*) FROM {row['table_name']}")
                print(f"  (Rows: {count})")
            except:
                pass

        await conn.close()
        
    except Exception as e:
        print(f"Error accessing database: {e}")

if __name__ == "__main__":
    asyncio.run(list_tables())
