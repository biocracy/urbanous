
import psycopg2
import os

# Connection string from .env
DB_URL = "postgresql://postgres:gYSJsRXSmBIAiSoucHtKuicMsibpuhwv@yamanote.proxy.rlwy.net:54565/railway"

try:
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()
    cur.execute("SELECT summary_markdown FROM news_digests WHERE id = 13;")
    row = cur.fetchone()
    if row and row[0]:
        with open("temp_digest_13.md", "w") as f:
            f.write(row[0])
        print("Saved summary to temp_digest_13.md")
    else:
        print("Digest #13 or summary not found.")
        
    cur.close()
    conn.close()
except Exception as e:
    print(f"Error: {e}")
