
import sqlite3
import os

DB_PATH = "urbanous.db"

def migrate():
    if not os.path.exists(DB_PATH):
        print("No database found, skipping migration.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Check if column exists
        cursor.execute("PRAGMA table_info(news_digests)")
        columns = [info[1] for info in cursor.fetchall()]
        
        if "selected_article_urls" not in columns:
            print("Adding selected_article_urls column...")
            cursor.execute("ALTER TABLE news_digests ADD COLUMN selected_article_urls TEXT")
            conn.commit()
            print("Migration successful.")
        else:
            print("Column selected_article_urls already exists.")
            
    except Exception as e:
        print(f"Migration failed: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
