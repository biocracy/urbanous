import logging
from sqlalchemy import text
from database import engine

logger = logging.getLogger(__name__)

async def run_migrations():
    """
    Checks for missing columns in news_digests and adds them if necessary.
    Safe to run on every startup.
    """
    logs = []
    
    def log(msg):
        print(msg)
        logs.append(msg)

    log("MIGRATION: Checking schema updates...")
    async with engine.begin() as conn:
        def check_column_exists(connection, table_name, column_name):
            from sqlalchemy import inspect
            inspector = inspect(connection)
            # Handle case where table doesn't exist yet
            if not inspector.has_table(table_name):
                return False
            columns = [c['name'] for c in inspector.get_columns(table_name)]
            return column_name in columns

        # 1. users.viz_settings
        has_column = await conn.run_sync(lambda c: check_column_exists(c, 'users', 'viz_settings'))
        if not has_column:
            log("MIGRATION: 'viz_settings' missing in 'users'. Adding...")
            try:
                await conn.execute(text("ALTER TABLE users ADD COLUMN viz_settings TEXT DEFAULT '{}'"))
                log("MIGRATION: Added 'viz_settings'.")
            except Exception as e:
                log(f"MIGRATION ERROR: {e}")
        else:
            log("MIGRATION: 'viz_settings' exists.")

        # 2. users.preferred_language
        has_column = await conn.run_sync(lambda c: check_column_exists(c, 'users', 'preferred_language'))
        if not has_column:
            log("MIGRATION: 'preferred_language' missing. Adding...")
            try:
                await conn.execute(text("ALTER TABLE users ADD COLUMN preferred_language VARCHAR DEFAULT 'English'"))
                log("MIGRATION: Added 'preferred_language'.")
            except Exception as e:
                log(f"MIGRATION ERROR: {e}")

        # 3. news_digests (cleanup older checks if needed, keeping core ones)
        has_public = await conn.run_sync(lambda c: check_column_exists(c, 'news_digests', 'is_public'))
        if not has_public:
            try:
                await conn.execute(text("ALTER TABLE news_digests ADD COLUMN is_public BOOLEAN DEFAULT FALSE"))
                log("MIGRATION: Added 'is_public'.")
            except Exception as e: log(f"Error {e}")

        has_slug = await conn.run_sync(lambda c: check_column_exists(c, 'news_digests', 'public_slug'))
        if not has_slug:
            try:
                await conn.execute(text("ALTER TABLE news_digests ADD COLUMN public_slug VARCHAR"))
                log("MIGRATION: Added 'public_slug'.")
            except Exception as e: log(f"Error {e}")
            
        has_created = await conn.run_sync(lambda c: check_column_exists(c, 'news_digests', 'created_at'))
        if not has_created:
            try:
                await conn.execute(text("ALTER TABLE news_digests ADD COLUMN created_at TIMESTAMP"))
                log("MIGRATION: Added 'created_at'.")
            except Exception as e: log(f"Error {e}")



    log("MIGRATION: Schema check complete.")
    
    # --- CLEANUP TASK: BROKEN IMAGES ---
    # Because of the Ephemeral Storage migration, many old IDs point to files that don't exist in the new Volume.
    # We should detect these and NULL them so the UI doesn't show broken images (and allows regeneration).
    import os
    DATA_DIR = os.getenv("DATA_DIR", ".")
    
    log("CLEANUP: Checking for orphaned images to facilitate regeneration...")
    
    # We need to run a SELECT, check file, then UPDATE.
    # Since we are in an `async with engine.begin() as conn` context above, we can't easily do complex logic with mapped objects.
    # But we can open a new session or just use raw SQL for the IDs.
    
    # Let's do it in a separate block to avoid transaction mess
    return logs

async def cleanup_broken_images():
    """
    Scans for digests with image_urls that do not exist on disk.
    Resets them to NULL.
    """
    from sqlalchemy.future import select
    from database import AsyncSessionLocal
    from models import NewsDigest
    import os
    
    DATA_DIR = os.getenv("DATA_DIR", ".")
    STATIC_ROOT = os.path.join(DATA_DIR, "static") # e.g. /app/data/static
    
    logs = []
    print("CLEANUP: Starting image verification...")
    
    async with AsyncSessionLocal() as db:
        try:
            stmt = select(NewsDigest).where(NewsDigest.image_url != None)
            result = await db.execute(stmt)
            digests = result.scalars().all()
            
            count_fixed = 0
            count_total = 0
            
            for digest in digests:
                count_total += 1
                if not digest.image_url: continue
                
                # Parse URL to File Path
                # URL: /static/digest_images/filename.png (or full url, or relative)
                # We expect: /static/digest_images/...
                
                url = digest.image_url
                filepath = None
                
                if "static/" in url:
                    # simplistic parsing: take everything after static/
                    # path join with STATIC_ROOT
                    rel_part = url.split("static/")[-1] 
                    filepath = os.path.join(STATIC_ROOT, rel_part)
                else:
                    # Unknown format, maybe absolute path from older bug?
                    # If it starts with /app/data, check that.
                    if url.startswith("/"):
                         # Try removing leading slash
                         filepath = os.path.join(DATA_DIR, url.lstrip("/"))
                
                if filepath:
                    if not os.path.exists(filepath):
                        print(f"CLEANUP: Broken Image Found (ID {digest.id}): URL={url}, Path={filepath} (Miss)")
                        digest.image_url = None
                        count_fixed += 1
                
            if count_fixed > 0:
                await db.commit()
                print(f"CLEANUP: Fixed {count_fixed} broken images (out of {count_total}).")
            else:
                print(f"CLEANUP: No broken images found (out of {count_total}).")
                
        except Exception as e:
            print(f"CLEANUP ERROR: {e}") 

