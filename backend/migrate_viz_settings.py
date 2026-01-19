import sqlite3
import os

DB_FILES = ["urbanous.db", "news.db", "sql_app.db"] # Check all potential DBs just in case

def migrate_db(db_path):
    if not os.path.exists(db_path):
        print(f"Skipping {db_path} (not found)")
        return

    print(f"Checking {db_path}...")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check if column exists
        cursor.execute("PRAGMA table_info(users)")
        columns = [info[1] for info in cursor.fetchall()]
        
        if "viz_settings" not in columns:
            print(f"Adding viz_settings to {db_path}...")
            cursor.execute("ALTER TABLE users ADD COLUMN viz_settings TEXT DEFAULT '{}'")
            conn.commit()
            print("Done.")
        else:
            print(f"Column viz_settings already exists in {db_path}.")
            
    except Exception as e:
        print(f"Error migrating {db_path}: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    print("Starting Migration: Add viz_settings to User model")
    # Base dir is where the script is run from usually, assume root or backend
    # We will try relative to backend first
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    for db_file in DB_FILES:
        # Try direct path
        path = os.path.join(base_dir, db_file)
        migrate_db(path)
