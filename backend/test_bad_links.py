
from scraper_engine import is_valid_article_url

bad_links = [
    "https://mlyn.by/privacy-policy/",
    "https://mlyn.by/usloviya-ispolzovaniya-informaczii-mlyn-by/",
    "https://mlyn.by/regions/minskaya-oblast/krupki/",
    "https://mlyn.by/regions/minskaya-oblast/marina-gorka/puhovichi/",
    "https://mlyn.by/regions/minskaya-oblast/kleczk/",
    "https://mlyn.by/regions/minskaya-oblast/starye-dorogi/",
    "https://mlyn.by/regions/minskaya-oblast/nesvizh/",
    "https://mlyn.by/regions/minskaya-oblast/dzerzhinsk/",
    "https://mlyn.by/regions/minskaya-oblast/zhodino/",
    "https://mlyn.by/regions/minskaya-oblast/molodechno/",
    "https://mlyn.by/regions/minskaya-oblast/borisov/",
    "https://shop.mlyn.by/",
    "https://mlyn.by/contacts/",
    "https://mlyn.by/lenta-novostej/",
    "http://alfaradio.by/about/feedback/",
    "http://alfaradio.by/about/received/",
    "http://alfaradio.by/about/contacts/",
    "http://alfaradio.by/about/logos/",
    "http://alfaradio.by/about/mesta-i-chastoty/",
    "http://alfaradio.by/about/",
    "http://alfaradio.by/events/",
    "http://alfaradio.by/budni/",
    "http://alfaradio.by/hits/",
    "mailto:info@afisha.me",
    "https://afisha.me/route/appear/smart/?l=https%3A%2F%2Fafisha.me%2F",
    "https://afisha.me/news/2/",
    "https://afisha.me/news/news/1314.html",
    "https://afisha.me/kids/",
    "https://afisha.me/other/",
    "https://afisha.me/online-events/",
    "https://www.threads.com/@nashaniva",
    "https://nashaniva.com/articles/",
    "https://nashaniva.com/feedback",
    "https://hotellook.tp.st/iqzm9YY6?erid=2VtzqvsRRBa",
    "https://nashaniva.com/latn/",
    "https://nashaniva.com/most-reacted/",
    "https://nashaniva.com/ca/652/",
    "https://patreon.com/nashaniva",
    "https://nashaniva.com/ru/202456",
    "http://www.zerkalo.io/page.php?page=terms",
    "http://www.zerkalo.io/unews/?utm_source=www.zerkalo.io&utm_medium=footer&utm_campaign=editorial_link",
    "https://invite.viber.com/?g2=AQAG6KinUuRDR0lUgJ5tahe1NyPFqJnsMVyVEyeTaPMAwPRdqk%2FU%2FSwlRXFJXl65&lang=ru",
    "http://www.zerkalo.io/route/appear/smart/?l=http%3A%2F%2Fsmart.zerkalo.io%2F",
    "https://news.zerkalo.io/cellar/117512.html",
    "https://news.zerkalo.io/cellar/117509.html",
    "https://news.zerkalo.io/?sort=time",
    "https://www.sb.by/cooperation/advertising/radio/",
    "http://www.sb.by/cooperation/advertising/publicity/",
    "https://sp.sb.by/brest1000",
    "http://sp.sb.by/heroes"
]

print(f"Testing {len(bad_links)} Provided Bad Links...")
allowed_count = 0
for url in bad_links:
    is_valid = is_valid_article_url(url)
    if is_valid:
        print(f"[ALLOWED] {url}")
        allowed_count += 1

print(f"\nResult: {allowed_count} / {len(bad_links)} were incorrectly allowed.")
