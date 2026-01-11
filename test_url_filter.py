import sys
import os

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from scraper_engine import is_valid_article_url

urls_to_test = [
    "https://bukinfo.com.ua/oblasna-vlada",  # Invalid (Category)
    "https://bukinfo.com.ua/parlamentski-vybory", # Invalid (Category)
    "https://bukinfo.com.ua/ukrajina", # Invalid (Category)
    "https://chas.cv.ua/comments/feed", # Invalid (Feed)
    "https://uk.wordpress.org/", # Invalid (Host)
    "https://promin.cv.ua/news/cv/crime/", # Invalid (Category)
    "https://promin.cv.ua/news/cv/sp/", # Invalid (Category)
    "https://le-vele.com.ua/ua/", # Invalid (Likely category)
    "https://ukr.radio/news/list.html?cat_id=36&channelID=1", # Invalid (List)
    "https://ukr.radio/reklama", # Invalid (Ads)
    "https://radio10.ua/aktsiyi.html", # Invalid (Promo)
    "https://valid-news.com/2025/01/01/some-cool-article", # Valid
    "https://valid-news.com/politics/long-article-slug-with-many-words", # Valid (long slug)
    "https://valid-news.com/news/12345", # Valid (ID)
]

print("Testing URL Filter...")
for url in urls_to_test:
    result = is_valid_article_url(url)
    status = "✅ PASS" if result else "❌ BLOCKED"
    print(f"{status}: {url}")

