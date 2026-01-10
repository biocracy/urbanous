import sqlite3

# Connect to the SQLite database
# Assuming the db file is "urbanous.db" based on 'database.py'
db_path = "urbanous.db"

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Add 'city' column
    try:
        print("Adding 'city' column...")
        cursor.execute("ALTER TABLE news_digests ADD COLUMN city VARCHAR")
        print("Success.")
    except Exception as e:
        print(f"Skipped 'city': {e}")

    # Add 'timeframe' column
    try:
        print("Adding 'timeframe' column...")
        cursor.execute("ALTER TABLE news_digests ADD COLUMN timeframe VARCHAR")
        print("Success.")
    except Exception as e:
        print(f"Skipped 'timeframe': {e}")
        
    conn.commit()
    conn.close()
    print("Migration complete.")

except Exception as e:
    print(f"Migration failed completely: {e}")
