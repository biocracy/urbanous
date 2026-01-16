
import asyncio
import asyncpg
import os
import json
from dotenv import load_dotenv

# Import the spam logic from our test file
# Note: We need to make sure test_spam_rules.py is in the python path or same dir
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from test_spam_rules import is_spam

load_dotenv('backend/.env')

DATABASE_URL = os.getenv("DATABASE_URL")

async def scan():
    print(f"Connecting to DB to scan digests...")
    if not DATABASE_URL:
        print("No DATABASE_URL found.")
        return

    conn = await asyncpg.connect(DATABASE_URL)
    
    rows = await conn.fetch('SELECT id, title, city, articles_json FROM news_digests ORDER BY id DESC')
    
    print(f"Found {len(rows)} digests. Scanning for spam...\n")
    
    total_articles = 0
    total_spam = 0
    
    for row in rows:
        digest_id = row['id']
        title = row['title'] or f"Digest #{digest_id}"
        city = row['city']
        
        try:
            articles = json.loads(row['articles_json'])
        except:
            print(f"[!] Warning: Could not parse JSON for Digest {digest_id}")
            continue
            
        digest_spam = []
        
        for art in articles:
            total_articles += 1
            url = art.get('url', '')
            # If URL is missing, skip
            if not url: continue
            
            reason = is_spam(url)
            if reason:
                digest_spam.append((url, reason, art.get('title', 'No Title')))
        
        if digest_spam:
            print(f"=== Digest: {title} ({city}) ===")
            print(f"Found {len(digest_spam)} spam items:")
            for url, reason, art_title in digest_spam:
                print(f"  [x] {reason}")
                print(f"      URL: {url}")
                print(f"      Title: {art_title}")
            print("")
            total_spam += len(digest_spam)
    
    print("-" * 40)
    print(f"Scan Complete.")
    print(f"Total Articles Scanned: {total_articles}")
    print(f"Total Spam Detected: {total_spam}")
    print(f"Spam Rate: {total_spam/total_articles*100:.1f}%")

    await conn.close()

if __name__ == "__main__":
    asyncio.run(scan())
