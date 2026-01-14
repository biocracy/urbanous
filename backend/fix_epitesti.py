import json
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import ScraperRule

# Connect to production DB
engine = create_engine("sqlite:///./urbanous.db", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def fix_epitesti():
    db = SessionLocal()
    try:
        domain = "epitesti.ro"
        rule = db.query(ScraperRule).filter(ScraperRule.domain == domain).first()
        
        if not rule:
            print(f"Creating new rule for {domain}")
            rule = ScraperRule(domain=domain, config_json="{}")
            db.add(rule)
        else:
            print(f"Updating existing rule for {domain}")
            
        config = json.loads(rule.config_json) if rule.config_json else {}
        
        # Apply Fixes
        config['title_selectors'] = ['h1.entry-title']
        config['date_selectors'] = ['time.entry-date', '.posted-on time']
        
        # Log change
        print(f"New Config: {json.dumps(config, indent=2)}")
        
        rule.config_json = json.dumps(config)
        db.commit()
        print("Successfully Saved!")
        
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    fix_epitesti()
