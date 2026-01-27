from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from google.api_core.exceptions import ResourceExhausted
from datetime import datetime

# --- Pydantic Schemas ---

class OutletCreate(BaseModel):
    name: str
    country_code: str
    city: str
    lat: Optional[float] = 0.0
    lng: Optional[float] = 0.0
    url: Optional[str] = None
    type: Optional[str] = "Unknown" # Print, Online, TV, Radio
    popularity: Optional[int] = 5
    focus: Optional[str] = "Local"

class OutletRead(BaseModel):
    id: int
    name: str
    country_code: str
    city: str
    lat: float
    lng: float
    url: Optional[str] = None
    type: Optional[str] = "Unknown"
    origin: Optional[str] = "auto"
    popularity: Optional[int] = 5
    focus: Optional[str] = "Local"
    
    class Config:
        from_attributes = True

class GeocodeRequest(BaseModel):
    city: str
    country: str

class GeocodeResponse(BaseModel):
    lat: float
    lng: float

class CityDiscoveryRequest(BaseModel):
    city: str
    country: str
    lat: Optional[float] = 0.0
    lng: Optional[float] = 0.0
    force_refresh: bool = False

class ImportUrlRequest(BaseModel):
    url: str
    city: str
    country: str
    lat: Optional[float] = 0.0

class CityInfoResponse(BaseModel):
    population: str
    description: str
    ruling_party: str
    flag_url: Optional[str] = None
    city_native_name: Optional[str] = None
    city_phonetic_name: Optional[str] = None
    country_flag_url: Optional[str] = None
    country_english: Optional[str] = None
    country_native: Optional[str] = None
    country_phonetic: Optional[str] = None

class PoliticsAssessmentRequest(BaseModel):
    url: str
    title: str
    content: Optional[str] = None # Optional, if frontend already has it or we re-fetch

class PoliticsAssessmentResponse(BaseModel):
    is_politics: bool
    confidence: int # 0-100
    reasoning: str
    labels: List[str] # e.g. ["POLITICS", "HEALTH"]

class OutletUpdate(BaseModel):
    url: Optional[str] = None
    name: Optional[str] = None

class KeywordData(BaseModel):
    word: str
    importance: int # 1-100
    type: str 
    sentiment: str
    source_urls: Optional[List[str]] = [] # New: Links to specific source articles

class ArticleMetadata(BaseModel):
    title: str
    url: str
    source: str
    image_url: Optional[str] = None
    date_str: Optional[str] = None
    relevance_score: Optional[int] = 0
    scores: Optional[Dict[str, Any]] = {}
    ai_verdict: Optional[str] = None # New field for AI Title Check status
    translated_title: Optional[str] = None # New field for Translation
    is_spam: Optional[bool] = False # Soft block status
    
class DigestResponse(BaseModel):
    digest: str
    articles: List[ArticleMetadata]
    analysis_source: Optional[List[KeywordData]] = []
    analysis_digest: Optional[List[KeywordData]] = []

class DigestSaveRequest(BaseModel):
    title: str
    category: str
    summary_markdown: str
    articles: List[ArticleMetadata]
    analysis_source: Optional[List[KeywordData]] = []
    analysis_digest: Optional[List[KeywordData]] = []

class DigestRead(BaseModel):
    id: int
    title: str
    category: str
    city: Optional[str] = None
    
    is_public: bool = False
    public_slug: Optional[str] = None
    
    created_at: str
    
    owner_id: int
    owner_username: Optional[str] = None
    owner_is_visible: bool = True

class DigestDetail(BaseModel):
    id: int
    title: str
    category: str
    timeframe: Optional[str] = "24h" # Added to support date calculation in frontend
    city: Optional[str] = None
    country: Optional[str] = None # Added for Metadata
    image_url: Optional[str] = None # Added for Metadata Images
    summary_markdown: str
    articles: List[Dict[str, Any]]
    analysis_source: Optional[List[Dict[str, Any]]] = []
    analysis_digest: Optional[List[Dict[str, Any]]] = []
    created_at: str
    owner_id: int
    owner_username: Optional[str] = None
    owner_is_visible: bool = True

class DigestRequest(BaseModel):
    outlet_ids: List[int]
    category: str
    timeframe: Optional[str] = "24h" # 24h, 3days, 1week
    city: Optional[str] = None

class DigestCreate(BaseModel):
    title: str
    category: str
    city: Optional[str] = None
    timeframe: Optional[str] = None
    summary_markdown: str
    articles: List[Dict[str, Any]] # Will be serialized to JSON
    selected_article_urls: Optional[List[str]] = None
    analysis_source: Optional[List[Dict[str, Any]]] = None # Will be serialized to JSON
    analysis_digest: Optional[List[Dict[str, Any]]] = None

class DigestSavedResponse(DigestCreate):
    id: int
    created_at: datetime
    is_public: bool = False
    public_slug: Optional[str] = None
    owner_id: int
    owner_username: Optional[str] = None
    owner_is_visible: bool = True
    
    class Config:
        from_attributes = True
