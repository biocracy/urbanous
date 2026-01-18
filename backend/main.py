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
    allow_origins=origins,
    # Allow Railway PRs (*.up.railway.app) AND Vercel Previews (*.vercel.app)
    allow_origin_regex=r"https://.*\.up\.railway\.app|https://.*\.vercel\.app", 
    allow_credentials=True,
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
static_dir = os.path.join(os.path.dirname(__file__), "static")
if not os.path.exists(static_dir):
    os.makedirs(static_dir)

app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/")
def read_root():
    return {"message": "Welcome to Urbanous API", "version": "v0.125.1 (Viz Settings Enabled)"}

@app.get("/fix-db")
async def manual_migration():
    """Manually trigger database schema migration and see logs."""
    logs = await run_migrations()
    return {"status": "completed", "logs": logs}
