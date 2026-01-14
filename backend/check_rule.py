import sys
import json
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base, ScraperRule

# Setup DB (assuming sqlite based on typical setup, or checking main.py)
# Check main.py or database.py for connection string? 
# Usually it's ./sql_app.db or similar.
# Let's assume standard local connection or try to import SessionLocal from database.py

try:
    from database import SessionLocal
except ImportError:
    # Fallback if database.py doesn't exist or export it
    engine = create_engine("sqlite:///./urbanous.db", connect_args={"check_same_thread": False})
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def check_epitesti():
    db = SessionLocal()
    try:
        # Search for epitesti
        rules = db.query(ScraperRule).filter(ScraperRule.domain.like("%epitesti%")).all()
        
        if not rules:
            print("No rules found for 'epitesti'")
            return
            
        for rule in rules:
            print(f"--- Rule for: {rule.domain} ---")
            try:
                config = json.loads(rule.config_json)
                print(json.dumps(config, indent=2))
            except:
                print(f"Raw Config (Parse Error): {rule.config_json}")
                
    finally:
        db.close()

if __name__ == "__main__":
    check_epitesti()
