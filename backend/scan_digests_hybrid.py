
import asyncio
import asyncpg
import os
import json
import httpx
import re
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import sys

# Import the rules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from test_spam_rules import is_spam

load_dotenv('backend/.env')
DATABASE_URL = os.getenv("DATABASE_URL")

# Configuration
MAX_CONCURRENT_REQUESTS = 10

async def analyze_content(client, url):
    """
    Fetches URL and returns (IsSpam, Reason) based on content.
    """
    try:
        resp = await client.get(url, timeout=10, follow_redirects=True)
        if resp.status_code != 200:
             return True, f"Content Unreachable ({resp.status_code})"
             
        html = resp.text
        soup = BeautifulSoup(html, 'html.parser')
        
        # 1. OG Type Check (Strong Signal)
        meta_type = soup.find("meta", property="og:type")
        if meta_type:
            og_type = meta_type.get("content", "").lower()
            if "article" in og_type:
                return False, f"Saved by og:type='{og_type}'"
        
        # 2. Link Density Check
        text = soup.get_text(" ", strip=True)
        if len(text) < 500:
             return True, "Content too short (Empty/JS-only)"
             
        links = soup.find_all("a")
        link_text_len = sum(len(a.get_text(strip=True)) for a in links)
        density = link_text_len / len(text)
        
        # 3. Paragraph Check
        paras = soup.find_all("p")
        significant_paras = [p for p in paras if len(p.get_text(strip=True)) > 80]
        
        # Decision Logic
        if density > 0.5 and len(significant_paras) < 3:
            return True, f"High Link Density ({density:.2f}) & Few Paragraphs ({len(significant_paras)})"
            
        if len(significant_paras) < 2:
             return True, "Too few significant paragraphs"

        return False, f"Safe (Density {density:.2f}, Paras {len(significant_paras)})"

    except Exception as e:
        return True, f"Fetch Error: {str(e)}"

async def process_digest(digest_id, title, city, articles, client, semaphore):
    results = []
    
    for art in articles:
        url = art.get('url', '')
        if not url: continue
        
        # 1. Run Static Rules
        rule_result = is_spam(url)
        
        if not rule_result:
            continue # Safe by static rules
            
        # 2. Classify Rule Severity
        is_hard_block = False
        if "Domain Block" in rule_result or "Subdomain Block" in rule_result or "Keyword Block" in rule_result:
            is_hard_block = True
            
        if is_hard_block:
            results.append((url, rule_result, art.get('title'), "HARD_BLOCK"))
            continue
            
        # 3. Soft Block -> Content Check
        async with semaphore:
            is_content_spam, content_reason = await analyze_content(client, url)
            
        if is_content_spam:
            final_reason = f"{rule_result} + {content_reason}"
            results.append((url, final_reason, art.get('title'), "SOFT_BLOCK"))
        else:
            # It was flagged by static rules but SAVED by content check
            # We can log this as a "Rescue" if we want, or just ignore it.
            # User wants to know "which links are spam", so we skip safe ones.
            pass
            
    return (title, city, results)

async def scan():
    print("Connecting to DB...")
    conn = await asyncpg.connect(DATABASE_URL)
    rows = await conn.fetch('SELECT id, title, city, articles_json FROM news_digests ORDER BY id DESC')
    await conn.close()
    
    print(f"Scanning {len(rows)} digests with Hybrid Content Analysis...")
    print("This may take a minute (fetching pages)...")
    
    headers = {"User-Agent": "Urbanous/SpamScanner/1.0"}
    
    total_spam = 0
    total_checked = 0
    
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)
    
    async with httpx.AsyncClient(headers=headers, verify=False, timeout=10) as client:
        tasks = []
        for row in rows:
            try:
                articles = json.loads(row['articles_json'])
                total_checked += len(articles)
                tasks.append(process_digest(row['id'], row['title'], row['city'], articles, client, semaphore))
            except: continue
            
        # Run all digests
        digest_results = await asyncio.gather(*tasks)
        
        # Print Report
        for title, city, spam_items in digest_results:
            if not spam_items: continue
            
            print(f"\n=== Digest: {title} ({city}) ===")
            print(f"Found {len(spam_items)} CONFIRMED spam items:")
            
            for url, reason, art_title, block_type in spam_items:
                mark = "[HARD]" if block_type == "HARD_BLOCK" else "[SOFT]"
                print(f"  {mark} {reason}")
                print(f"      URL: {url}")
                print(f"      Title: {art_title}")
                
            total_spam += len(spam_items)

    print("-" * 40)
    print(f"Analysis Complete.")
    print(f"Total Articles: {total_checked}")
    print(f"Confirmed Spam: {total_spam}")
    print(f"Spam Rate: {total_spam/total_checked*100:.1f}%")

if __name__ == "__main__":
    asyncio.run(scan())
