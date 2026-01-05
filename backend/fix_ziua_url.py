import sqlite3

DB_PATH = "urbanous.db"

def fix_url():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Check current URL
    cursor.execute("SELECT id, name, url FROM news_outlets WHERE url LIKE '%ziuadeconstanta%'")
    rows = cursor.fetchall()
    
    print("Found outlets:", rows)
    
    for row in rows:
        oid, name, url = row
        if "https://" in url:
            new_url = url.replace("https://", "http://")
            print(f"Updating {name}: {url} -> {new_url}")
            cursor.execute("UPDATE news_outlets SET url = ? WHERE id = ?", (new_url, oid))
            
    conn.commit()
    conn.close()
    print("Fix complete.")

if __name__ == "__main__":
    fix_url()
