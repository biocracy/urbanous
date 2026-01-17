from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.orm import Session
from pydantic import BaseModel
from models import User
from security import verify_password, get_password_hash, create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES
from dependencies import get_db, get_current_user
from datetime import datetime, timedelta, timezone

router = APIRouter()

class UserCreate(BaseModel):
    email: str
    password: str
    username: str | None = None
    gemini_api_key: str | None = None

class Token(BaseModel):
    access_token: str
    token_type: str

import uuid
from utils.email import send_verification_email, send_reset_password_email

class ForgotPasswordRequest(BaseModel):
    email: str

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

@router.post("/register")
async def register(user: UserCreate, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    # Check existing
    result = await db.execute(select(User).where(User.email == user.email))
    if result.scalars().first():
        raise HTTPException(status_code=400, detail="Email already registered")
    
    hashed_pw = get_password_hash(user.password)
    verification_token = str(uuid.uuid4())
    
    db_user = User(
        email=user.email,
        username=user.username,
        hashed_password=hashed_pw,
        gemini_api_key=user.gemini_api_key,
        is_verified=False,
        verification_token=verification_token,
        is_username_visible=True # Default to visible
    )
    db.add(db_user)
    await db.commit()
    
    # Send Email in background (prevents timeout)
    background_tasks.add_task(send_verification_email, user.email, verification_token)
    
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

@router.post("/forgot-password")
async def forgot_password(request: ForgotPasswordRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == request.email))
    user = result.scalars().first()
    
    if user:
        token = str(uuid.uuid4())
        user.reset_token = token
        user.reset_token_expires = datetime.now(timezone.utc) + timedelta(hours=1)
        await db.commit()
        
        background_tasks.add_task(send_reset_password_email, user.email, token)
        
    return {"message": "If the email is registered, a reset link has been sent."}

@router.post("/reset-password")
async def reset_password(request: ResetPasswordRequest, db: Session = Depends(get_db)):
    result = await db.execute(select(User).where(User.reset_token == request.token))
    user = result.scalars().first()
    
    if not user:
        raise HTTPException(status_code=400, detail="Invalid or used token")
        
    if user.reset_token_expires:
        expires = user.reset_token_expires
        # Handle case where DB returns string (due to TEXT column type)
        if isinstance(expires, str):
            try:
                expires = datetime.fromisoformat(expires)
            except ValueError:
                # If parsing fails, invalidate token
                raise HTTPException(status_code=400, detail="Token data corrupted")
        
        # Ensure timezone awareness (assume UTC if naive)
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
            
        if expires < datetime.now(timezone.utc):
            raise HTTPException(status_code=400, detail="Token expired")
        
    user.hashed_password = get_password_hash(request.new_password)
    user.reset_token = None
    user.reset_token_expires = None
    await db.commit()
    
    return {"message": "Password reset successfully. You can now login."}

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
    username: str | None = None
    is_username_visible: bool | None = None
    viz_settings: str | None = None # New: JSON String from frontend

@router.get("/users/me")
async def read_users_me(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "email": current_user.email,
        "username": current_user.username,
        "is_username_visible": current_user.is_username_visible,
        "gemini_api_key": current_user.gemini_api_key, 
        "preferred_language": current_user.preferred_language,
        "viz_settings": current_user.viz_settings, # Return Persisted Settings
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
        
        # New: Update Viz Settings
        if settings.viz_settings is not None:
            user_in_db.viz_settings = settings.viz_settings
            
        if settings.username is not None:
            # Check Uniqueness
            if settings.username != user_in_db.username:
                existing = await db.execute(select(User).where(User.username == settings.username))
                if existing.scalars().first():
                     raise HTTPException(status_code=400, detail="Username already taken")
                user_in_db.username = settings.username
        
        if settings.is_username_visible is not None:
            user_in_db.is_username_visible = settings.is_username_visible
            
        await db.commit()
        return {"status": "Updated Settings"}
    raise HTTPException(status_code=404, detail="User not found")
            
        await db.commit()
        return {"status": "Updated Settings"}
    raise HTTPException(status_code=404, detail="User not found")

# Backward compatibility alias (Optional, but safer for split-second deployment)
@router.put("/users/me/api-key")
async def update_api_key_legacy(body: UserSettingsUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return await update_user_settings(body, current_user, db)
