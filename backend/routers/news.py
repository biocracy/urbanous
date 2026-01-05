import os
import httpx
from fastapi import APIRouter, Query
from typing import List, Optional
from pydantic import BaseModel

router = APIRouter()

class Article(BaseModel):
    title: str
    url: str
    source: str
    publishedAt: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None

@router.get("/news", response_model=List[Article])
async def get_news(country: str = Query(..., description="2-letter ISO country code")):
    api_key = os.getenv("NEWS_API_KEY")
    
    if not api_key:
        # Return Mock Data for Demo/Dev
        print(f"No NEWS_API_KEY found. returning mock data for {country}")
        return [
            Article(
                title=f"Breaking News in {country}: Local Economy Booms",
                url="https://example.com/news/1",
                source="The Daily Mock",
                publishedAt="2025-10-27T10:00:00Z"
            ),
            Article(
                title=f"Technology Summit Held in {country}",
                url="https://example.com/news/2",
                source="TechWorld",
                publishedAt="2025-10-26T14:30:00Z"
            ),
            Article(
                title=f"New environmental policies announced for {country}",
                url="https://example.com/news/3",
                source="Green Planet",
                publishedAt="2025-10-25T09:15:00Z"
            ),
             Article(
                title=f"Sports Update: {country} wins regional championship",
                url="https://example.com/news/4",
                source="SportsCentral",
                publishedAt="2025-10-28T18:00:00Z"
            )
        ]

    # Real API Call
    url = f"https://newsapi.org/v2/top-headlines?country={country.lower()}&apiKey={api_key}"
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()
            
            articles = []
            for item in data.get("articles", []):
                # We do NOT have geocoding here yet, so we return null lat/lng
                # The Frontend handles random distribution.
                articles.append(Article(
                    title=item.get("title"),
                    url=item.get("url"),
                    source=item.get("source", {}).get("name", "Unknown"),
                    publishedAt=item.get("publishedAt")
                ))
            return articles
            
        except Exception as e:
            print(f"Error fetching news: {e}")
            return []
