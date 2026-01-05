
import sqlite3
import os

DB_PATH = "memex.db"

def migrate():
    if not os.path.exists(DB_PATH):
        print(f"Database {DB_PATH} not found.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print("Checking 'news_digests' table schema...")
    cursor.execute("PRAGMA table_info(news_digests)")
    columns = [info[1] for info in cursor.fetchall()]
    print(f"Current columns: {columns}")
    
    if "analysis_source" not in columns:
        print("Adding 'analysis_source' column...")
        try:
            cursor.execute("ALTER TABLE news_digests ADD COLUMN analysis_source TEXT")
            print("Added 'analysis_source'.")
        except Exception as e:
            print(f"Error adding 'analysis_source': {e}")

    if "analysis_digest" not in columns:
        print("Adding 'analysis_digest' column...")
        try:
            cursor.execute("ALTER TABLE news_digests ADD COLUMN analysis_digest TEXT")
            print("Added 'analysis_digest'.")
        except Exception as e:
            print(f"Error adding 'analysis_digest': {e}")
            
    conn.commit()
    conn.close()
    print("Migration complete.")

if __name__ == "__main__":
    migrate()
