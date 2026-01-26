from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import engine, Base
from routers import auth, outlets, scraper, feedback
from models import User, NewsOutlet, NewsDigest # Import to register models
import os
from auto_migrate import run_migrations

app = FastAPI(title="Urbanous API")

# CORS
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "https://urbanous.vercel.app",
    "https://urbanous.net",
    "https://www.urbanous.net"
]

# Allow specific override if set (e.g. for staging)
frontend_env = os.getenv("FRONTEND_URL")
if frontend_env and frontend_env != "*":
    origins.append(frontend_env)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    # Allow Railway PRs (*.up.railway.app) AND Vercel Previews (*.vercel.app)
    allow_origin_regex=r"https://.*\.up\.railway\.app|https://.*\.vercel\.app", 
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS", "PUT", "DELETE"],
    allow_headers=["*"],
)

# Startup
@app.on_event("startup")
async def startup():
    try:
        print("STARTUP: Initializing Database...")
        # In dev/standalone, create tables if not exist
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        # Run Schema Updates (Add missing columns)
        print("STARTUP: Running Auto-Migrations...")
        await run_migrations()
        
        # Run Data Cleanup (Broken Images)
        from auto_migrate import cleanup_broken_images
        await cleanup_broken_images()
        
        print("STARTUP: Complete.")
    except Exception as e:
        # CRITICAL: Do NOT crash. Log and continue so /debug endpoint works.
        print(f"STARTUP ERROR: {e}") 

@app.get("/debug/schema")
async def debug_schema():
    """Inspect the database columns remotely."""
    try:
        from sqlalchemy import text
        logs = []
        async with engine.begin() as conn:
            # Check users
            try:
                # Portable way to check columns might be DB specific, but raw SQL PRAGMA or Query schema works
                # Just try to select all columns
                await conn.execute(text("SELECT id, viz_settings FROM users LIMIT 1"))
                logs.append("SUCCESS: viz_settings column handles SELECT.")
            except Exception as e:
                logs.append(f"FAIL: SELECT viz_settings errored: {e}")
                
        return {"status": "debug", "logs": logs}
    except Exception as e:
        return {"status": "error", "error": str(e)}

# Routers
app.include_router(auth.router, tags=["Authentication"])
app.include_router(outlets.router, tags=["News Agents"])
app.include_router(scraper.router, tags=["Scraper Config"])
app.include_router(feedback.router, tags=["Feedback System"])

from fastapi.staticfiles import StaticFiles

# ... code ...

# Mount Static Files for Clusters
# Ensure directory exists to prevent startup error
# Mount Static Files for Clusters & Images
# Support for Persistent Volume (DATA_DIR)
# Support for Persistent Volume (DATA_DIR)
DATA_DIR = os.getenv("DATA_DIR")
if not DATA_DIR:
    if os.path.exists("/app/data"):
        DATA_DIR = "/app/data"
    else:
        DATA_DIR = "."
static_dir = os.path.join(DATA_DIR, "static")

# Ensure directory exists to prevent startup error
if not os.path.exists(static_dir):
    os.makedirs(static_dir)

# Also ensure specific subdirs exist if volume was just created
for subdir in ["digest_images", "clusters", "flags"]:
    s_path = os.path.join(static_dir, subdir)
    if not os.path.exists(s_path):
        os.makedirs(s_path)

# --- CRITICAL: SYNC LOCAL STATIC ASSETS TO VOLUME ---
# Since we are mounting the Volume version of 'static', it might be empty on first run.
# We must copy the app's original static assets (like clusters/*.json or placeholders) into it.
import shutil

local_static = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(local_static):
    # Sync specific important folders
    for item in os.listdir(local_static):
        src_path = os.path.join(local_static, item)
        dst_path = os.path.join(static_dir, item)
        
        if os.path.isdir(src_path):
            # Sync Directory
            print(f"STORAGE: Syncing {item} to Volume...")
            # dirs_exist_ok=True allows overwriting/updating existing folder
            # ignoring errors to be safe? No, we want to know.
            try:
                shutil.copytree(src_path, dst_path, dirs_exist_ok=True)
            except Exception as e:
                print(f"STORAGE ERROR: Failed to sync {item}: {e}")

        elif os.path.isfile(src_path):
            # Copy root static files (like placeholders)
            if not os.path.exists(dst_path):
                shutil.copy2(src_path, dst_path)
                
print(f"STORAGE: Static files mounted at {os.path.abspath(static_dir)}")
app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/")
def read_root():
    return {"message": "Welcome to Urbanous API", "version": "v0.133 (Viz Settings Enabled)"}

@app.get("/fix-db")
async def manual_migration():
    """Manually trigger database schema migration and see logs."""
    logs = await run_migrations()
    return {"status": "completed", "logs": logs}
