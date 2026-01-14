from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import select
from database import AsyncSessionLocal
from models import SpamFeedback, User
from routers.auth import get_current_user # Assuming we wantauth
from typing import Optional

router = APIRouter(prefix="/feedback", tags=["Feedback"])

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

class SpamReportRequest(BaseModel):
    url: str
    title: Optional[str] = None
    reason: Optional[str] = "spam"

@router.post("/spam", status_code=status.HTTP_201_CREATED)
async def report_spam(
    report: SpamReportRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Report an article as spam/noise.
    """
    # Normalize domain
    from urllib.parse import urlparse
    try:
        domain = urlparse(report.url).netloc.replace("www.", "")
    except:
        domain = "unknown"

    feedback = SpamFeedback(
        url=report.url,
        domain=domain,
        title=report.title,
        reason=report.reason
    )
    
    db.add(feedback)
    await db.commit()
    
    return {"status": "reported", "id": feedback.id}

@router.delete("/spam", status_code=status.HTTP_200_OK)
async def delete_spam_report(
    url: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Remove a spam report (Undo).
    """
    stmt = select(SpamFeedback).where(SpamFeedback.url == url)
    result = await db.execute(stmt)
    feedbacks = result.scalars().all()
    
    if not feedbacks:
        return {"status": "not_found", "message": "No report found for this URL"}
        
    for f in feedbacks:
        await db.delete(f)
        
    await db.commit()
    return {"status": "deleted", "count": len(feedbacks)}
