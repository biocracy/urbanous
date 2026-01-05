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

@router.post("/register", response_model=Token)
async def register(user: UserCreate, db: Session = Depends(get_db)):
    # Check existing
    result = await db.execute(select(User).where(User.email == user.email))
    if result.scalars().first():
        raise HTTPException(status_code=400, detail="Email already registered")
    
    hashed_pw = get_password_hash(user.password)
    db_user = User(
        email=user.email,
        hashed_password=hashed_pw,
        gemini_api_key=user.gemini_api_key
    )
    db.add(db_user)
    await db.commit()
    
    # Auto-login
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

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
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

class APIKeyUpdate(BaseModel):
    api_key: str

@router.get("/users/me")
async def read_users_me(current_user: User = Depends(get_current_user)):
    return {
        "email": current_user.email,
        "gemini_api_key": current_user.gemini_api_key, # In prod, mask this? For now, nice for UX to see it.
        "created_at": current_user.created_at
    }

@router.put("/users/me/api-key")
async def update_api_key(valid_body: APIKeyUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # Re-fetch user in the current session to ensure it's attached and tracked
    result = await db.execute(select(User).where(User.id == current_user.id))
    user_in_db = result.scalars().first()
    
    if user_in_db:
        user_in_db.gemini_api_key = valid_body.api_key
        await db.commit()
        return {"status": "Updated API Key"}
    raise HTTPException(status_code=404, detail="User not found")
