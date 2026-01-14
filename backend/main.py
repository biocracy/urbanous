from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import engine, Base
from routers import auth, outlets, scraper, feedback
from models import User, NewsOutlet, NewsDigest # Import to register models
import os

app = FastAPI(title="Urbanous API")

# CORS
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "https://urbanous.vercel.app",
    "https://urbanous.net",
    "https://www.urbanous.net",
    # Allow Railway generated domains
    "https://urbanous-production.up.railway.app",
    os.getenv("FRONTEND_URL", "*")  # Fallback to wildcard if specified, or specific URL
]

# For debugging connection issues, we can temporarily allow all if needed, but best to be specific.
# If FRONTEND_URL is set to '*', allow_origins should be ['*']
if os.getenv("FRONTEND_URL") == "*":
    origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Startup
@app.on_event("startup")
async def startup():
    # In dev/standalone, create tables if not exist
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

# Routers
app.include_router(auth.router, tags=["Authentication"])
app.include_router(outlets.router, tags=["News Agents"])
app.include_router(scraper.router, tags=["Scraper Config"])
app.include_router(feedback.router, tags=["Feedback System"])

@app.get("/")
def read_root():
    return {"message": "Welcome to Urbanous API", "version": "v0.106"}
