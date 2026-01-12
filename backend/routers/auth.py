from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.orm import Session
from pydantic import BaseModel
from models import User
from security import verify_password, get_password_hash, create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES
from dependencies import get_db, get_current_user
from datetime import timedelta

router = APIRouter()

class UserCreate(BaseModel):
    email: str
    password: str
    gemini_api_key: str | None = None

class Token(BaseModel):
    access_token: str
    token_type: str

import uuid
from utils.email import send_verification_email

@router.post("/register")
async def register(user: UserCreate, db: Session = Depends(get_db)):
    # Check existing
    result = await db.execute(select(User).where(User.email == user.email))
    if result.scalars().first():
        raise HTTPException(status_code=400, detail="Email already registered")
    
    hashed_pw = get_password_hash(user.password)
    verification_token = str(uuid.uuid4())
    
    db_user = User(
        email=user.email,
        hashed_password=hashed_pw,
        gemini_api_key=user.gemini_api_key,
        is_verified=False,
        verification_token=verification_token
    )
    db.add(db_user)
    await db.commit()
    
    # Send Email (Background task ideal, but direct await for simplicity/feedback)
    try:
        await send_verification_email(user.email, verification_token)
    except Exception as e:
        print(f"Error sending email: {e}")
        # We don't rollback user, but user receives error? Or just "Check email"?
        # If email fails, user is stuck.
        # Ideally we rollback or allow resend.
        # For prototype: Log error, tell user to check email/contact support.
    
    return {"message": "Registration successful. Please check your email to verify your account."}

@router.get("/verify")
async def verify_email(token: str, db: Session = Depends(get_db)):
    result = await db.execute(select(User).where(User.verification_token == token))
    user = result.scalars().first()
    
    if not user:
        raise HTTPException(status_code=400, detail="Invalid verification token")
    
    if user.is_verified:
         return {"message": "Email already verified"}

    user.is_verified = True
    user.verification_token = None
    await db.commit()
    
    return {"message": "Email verified successfully. You can now login."}

@router.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == form_data.username)) # OAuth2 spec calls it username
    user = result.scalars().first()
    
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    if not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email not verified. Please check your inbox.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

class UserSettingsUpdate(BaseModel):
    api_key: str | None = None
    preferred_language: str | None = None

@router.get("/users/me")
async def read_users_me(current_user: User = Depends(get_current_user)):
    return {
        "email": current_user.email,
        "gemini_api_key": current_user.gemini_api_key, 
        "preferred_language": current_user.preferred_language, # New Field
        "created_at": current_user.created_at
    }

@router.put("/users/me/settings")
async def update_user_settings(settings: UserSettingsUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # Re-fetch user
    result = await db.execute(select(User).where(User.id == current_user.id))
    user_in_db = result.scalars().first()
    
    if user_in_db:
        if settings.api_key is not None:
            user_in_db.gemini_api_key = settings.api_key
        if settings.preferred_language is not None:
            user_in_db.preferred_language = settings.preferred_language
            
        await db.commit()
        return {"status": "Updated Settings"}
    raise HTTPException(status_code=404, detail="User not found")

# Backward compatibility alias (Optional, but safer for split-second deployment)
@router.put("/users/me/api-key")
async def update_api_key_legacy(body: UserSettingsUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return await update_user_settings(body, current_user, db)
