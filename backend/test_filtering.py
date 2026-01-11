import sys
import os

# Add path
sys.path.append(os.getcwd())
try:
    from scraper_engine import is_valid_article_url
except ImportError:
    # If not in scraper_engine, try to find where it is or mock it based on known logic
    # Step 1159 confirmed it is in scraper_engine.py
    print("Could not import is_valid_article_url")
    sys.exit(1)

urls = [
    "https://vesti92.ru/results-of-2025/",
    "https://vesti92.ru/incidents/the-duty-station/",
    "https://vesti92.ru/news-releases/vesti-utro-sevastopol/",
    "https://vesti92.ru/news-releases/events-of-the-week/",
    "https://vesti92.ru/from-sevastopol-to-berlin/",
    "https://vesti92.ru/stories-in-stone/",
    "https://vesti92.ru/they-saw-the-war/",
    "https://vesti92.ru/crimean-offensive-operation/",
    "https://vesti92.ru/lastnews/",
    "https://vesti92.ru/incidents/",
    "https://vesti92.ru/vestifm/",
    "https://vesti92.ru/story/",
    "https://vesti92.ru/news-releases/",
    "https://vesti92.ru/interview/",
    "https://vesti92.ru/the-duty-station/",
    "https://vesti92.ru/admirals-tea/",
    "https://vesti92.ru/military-chronicle/",
    "https://vesti92.ru/about-us.html",
    "https://vesti92.ru/contacts.html",
    "https://vesti92.ru/job-openings.html",
    "https://vesti92.ru/documents.html",
    "https://vesti92.ru/?do=feedback",
    "https://vesti92.ru/advertisement.html",
    "https://vesti92.ru/index.php?do=lostpassword"
]

print(f"{'URL':<60} | {'Is Article?':<10}")
print("-" * 75)

passed = 0
failed = 0

for url in urls:
    is_article = is_valid_article_url(url)
    status = "✅ YES" if is_article else "❌ NO"
    if is_article: passed += 1
    else: failed += 1
    print(f"{url:<60} | {status}")

print("-" * 75)
print(f"Total: {len(urls)}, Articles: {passed}, Rejected: {failed}")
