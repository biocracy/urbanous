import logging
from sqlalchemy import text
from database import engine

logger = logging.getLogger(__name__)

async def run_migrations():
    """
    Checks for missing columns in news_digests and adds them if necessary.
    Safe to run on every startup.
    """
    print("MIGRATION: Checking schema updates...")
    async with engine.begin() as conn:
        # 1. Check for 'is_public'
        try:
            # Attempt to select the column to see if it exists
            await conn.execute(text("SELECT is_public FROM news_digests LIMIT 1"))
            print("MIGRATION: 'is_public' column exists.")
        except Exception:
            print("MIGRATION: 'is_public' missing. Adding column...")
            # Detect DB Type logic (Postgres vs SQLite)
            # Simplified: Use standard ADD COLUMN which works for both in this case (mostly)
            # Actually SQLite ALTER TABLE is limited but ADD COLUMN is supported.
            try:
                await conn.execute(text("ALTER TABLE news_digests ADD COLUMN is_public BOOLEAN DEFAULT FALSE"))
                print("MIGRATION: Added 'is_public'.")
            except Exception as e:
                print(f"MIGRATION ERROR adding is_public: {e}")

        # 2. Check for 'public_slug'
        try:
            await conn.execute(text("SELECT public_slug FROM news_digests LIMIT 1"))
            print("MIGRATION: 'public_slug' column exists.")
        except Exception:
            print("MIGRATION: 'public_slug' missing. Adding column...")
            try:
                await conn.execute(text("ALTER TABLE news_digests ADD COLUMN public_slug VARCHAR"))
                print("MIGRATION: Added 'public_slug'.")
            except Exception as e:
                print(f"MIGRATION ERROR adding public_slug: {e}")
                
        # 3. Check for 'created_at' (just in case)
        try:
            await conn.execute(text("SELECT created_at FROM news_digests LIMIT 1"))
        except Exception:
             print("MIGRATION: 'created_at' missing. Adding column...")
             try:
                 # SQLite doesn't support adding column with default timestamp easily in same statement
                 await conn.execute(text("ALTER TABLE news_digests ADD COLUMN created_at TIMESTAMP"))
             except Exception as e:
                 print(f"MIGRATION ERROR adding created_at: {e}")

    print("MIGRATION: Schema check complete.")
