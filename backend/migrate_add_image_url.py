import sqlite3
import os

DB_PATH = "urbanous.db"  # Corrected from database.py defaults

def migrate():
    print("MIGRATION: Adding 'image_url' column to news_digests...")
    
    if not os.path.exists(DB_PATH):
        print(f"ERROR: Database file {DB_PATH} not found.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # Check if column exists
        cursor.execute("PRAGMA table_info(news_digests)")
        columns = [info[1] for info in cursor.fetchall()]
        
        if "image_url" in columns:
            print("SKIPPED: 'image_url' column already exists.")
        else:
            cursor.execute("ALTER TABLE news_digests ADD COLUMN image_url TEXT")
            conn.commit()
            print("SUCCESS: Added 'image_url' column.")
            
    except Exception as e:
        print(f"ERROR: Migration failed: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
