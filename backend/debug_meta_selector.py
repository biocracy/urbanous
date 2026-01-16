
import sys
import os
sys.path.append(os.getcwd())
from backend.scraper_engine import extract_date_from_html, ScraperRule

html = """
<head>
    <meta http-equiv="refresh" content="300">
    <base href="../..">
    <script>console.log('--> deu')</script><title>Jefe de la CIA llegó a Caracas</title>
	<meta property="article:published_time" content="16/01/2026 02:14 pm" />
	<meta property="article:modified_time" content="2026/01/16 14:25:36" />
"""

rule = ScraperRule(
    domain="test.com",
    date_selectors=['meta[property="article:published_time"]'],
    date_regex=[r"(\d{2}/\d{2}/\d{4})"] # Optional, engine might handle full string via parse_romanian_date
)

print("--- Testing Meta Selector ---")
res = extract_date_from_html(html, "http://test.com", custom_rule_override=rule)
print(f"Result: {res}")
