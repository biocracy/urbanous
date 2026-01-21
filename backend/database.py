import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base


# 1. Try to get the explicit Railway/Postgres URL first
env_db_url = os.getenv("DATABASE_URL")

# 2. If valid Postgres URL, use it
if env_db_url and "postgres" in env_db_url:
    print(f"DATABASE: Connecting to PostgreSQL")
    DATABASE_URL = env_db_url
else:
    # 3. Fallback to SQLite (Volume or Local)
    # Only use DATA_DIR for SQLite
    DATA_DIR = os.getenv("DATA_DIR", ".")
    print(f"DATABASE: Using SQLite in {DATA_DIR}")
    DATABASE_URL = f"sqlite+aiosqlite:///{os.path.join(DATA_DIR, 'urbanous.db')}"

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+asyncpg://", 1)
elif DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

engine = create_async_engine(DATABASE_URL, echo=True)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()

