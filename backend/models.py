from sqlalchemy import Column, Integer, String, DateTime, Boolean, Float, ForeignKey, text, select, func, Table
from sqlalchemy.orm import relationship
from database import Base

# --- User Model ---
class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    gemini_api_key = Column(String, nullable=True) # Encrypted ideally, plain for MVP
    preferred_language = Column(String, default="English") # New: Translation Preference
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    digests = relationship("NewsDigest", back_populates="user")
    # outlets? If we want private outlets

# --- News Models ---

class NewsOutlet(Base):
    __tablename__ = "news_outlets"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    country_code = Column(String, index=True) # ISO A2 e.g. "US"
    city = Column(String)
    lat = Column(Float)
    lng = Column(Float)
    url = Column(String, nullable=True)
    type = Column(String, default="Unknown")
    origin = Column(String, default="auto") # 'auto' or 'manual'
    popularity = Column(Integer, default=5) # 1-10 score
    focus = Column(String, default="Local") # Local, National, or Mixed
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Country(Base):
    __tablename__ = "countries"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True) # English Name
    native_name = Column(String, nullable=True)
    phonetic_name = Column(String, nullable=True)
    flag_url = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    cities = relationship("CityMetadata", back_populates="country")

class CityMetadata(Base):
    __tablename__ = "city_metadata"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    native_name = Column(String, nullable=True)
    phonetic_name = Column(String, nullable=True)
    country_id = Column(Integer, ForeignKey("countries.id"))
    
    population = Column(String, nullable=True)
    description = Column(String, nullable=True)
    ruling_party = Column(String, nullable=True)
    flag_url = Column(String, nullable=True) # City Coat of Arms
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    country = relationship("Country", back_populates="cities")

class NewsDigest(Base):
    __tablename__ = "news_digests"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id")) # Link to User
    
    title = Column(String)
    category = Column(String)
    city = Column(String, nullable=True) # New: City Name
    timeframe = Column(String, nullable=True) # New: Timeframe used (e.g. 24h)
    summary_markdown = Column(String)
    articles_json = Column(String) # JSON string of list of articles metadata
    analysis_source = Column(String, nullable=True) # JSON string of keyword analysis
    analysis_digest = Column(String, nullable=True) # JSON string of keyword analysis
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    user = relationship("User", back_populates="digests")

# --- Scraper Rule Model ---
class ScraperRule(Base):
    __tablename__ = "scraper_rules"
    
    id = Column(Integer, primary_key=True, index=True)
    domain = Column(String, unique=True, index=True) # e.g. "tribuna.ro"
    
    # Configuration JSON stored as String
    # {
    #   "date_selectors": [".post-date"],
    #   "use_json_ld": true,
    #   "use_data_layer": false,
    #   "data_layer_var": "dataLayer"
    # }
    config_json = Column(String) 
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

# Keep Category if needed for tagging digests, but for now String category is simpler.
