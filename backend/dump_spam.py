
import asyncio
import asyncpg
import os
import json
from dotenv import load_dotenv

load_dotenv('backend/.env')

DATABASE_URL = os.getenv("DATABASE_URL")

async def dump_spam():
    print(f"Connecting to DB...")
    conn = await asyncpg.connect(DATABASE_URL)
    
    rows = await conn.fetch('SELECT url, reason, domain, title FROM spam_feedback ORDER BY domain')
    
    data = [dict(r) for r in rows]
    
    with open('backend/spam_urls.json', 'w') as f:
        json.dump(data, f, indent=2)
        
    print(f"Dumped {len(data)} items to backend/spam_urls.json")
    await conn.close()

if __name__ == "__main__":
    asyncio.run(dump_spam())
