import sqlite3
import os

DB_PATH = "urbanous.db"

def assign_placeholders():
    print("ASSIGNMENT: Assigning placeholder images to existing digests...")
    
    if not os.path.exists(DB_PATH):
        print(f"ERROR: Database file {DB_PATH} not found.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # Update all rows where image_url is NULL or empty
        cursor.execute("""
            UPDATE news_digests 
            SET image_url = '/static/digest_images/placeholder.png' 
            WHERE image_url IS NULL OR image_url = ''
        """)
        
        updated_count = cursor.rowcount
        conn.commit()
        
        print(f"SUCCESS: Updated {updated_count} digests with placeholder image.")
            
    except Exception as e:
        print(f"ERROR: Assignment failed: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    assign_placeholders()
