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
             log("MIGRATION: 'created_at' missing. Adding column...")
             try:
                 # SQLite doesn't support adding column with default timestamp easily in same statement
                 await conn.execute(text("ALTER TABLE news_digests ADD COLUMN created_at TIMESTAMP"))
             except Exception as e:
                 log(f"MIGRATION ERROR adding created_at: {e}")

    log("MIGRATION: Schema check complete.")
    return logs
