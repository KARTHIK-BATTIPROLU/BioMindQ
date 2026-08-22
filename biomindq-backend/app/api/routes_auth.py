import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from pydantic import BaseModel, EmailStr, Field
from fastapi import APIRouter, HTTPException, Depends, status, Response, Request
from app.auth.security import (
    hash_password, verify_password, create_access_token, create_refresh_token, decode_token
)
from app.auth.dependencies import get_current_user
from app.db.mongo import mongo_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])

class UserRegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)

class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str

class TokenRefreshRequest(BaseModel):
    refresh_token: str

class UserResponse(BaseModel):
    id: str
    email: str
    plan: str
    created_at: Optional[datetime] = None

class AuthResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse

@router.post("/register", response_model=AuthResponse)
async def register_user(body: UserRegisterRequest, response: Response):
    email = body.email.lower().strip()
    if mongo_manager.db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection is not available."
        )

    existing_user = await mongo_manager.db["users"].find_one({"email": email})
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email address already exists."
        )

    hashed = hash_password(body.password)
    now = datetime.now(timezone.utc)
    user_doc = {
        "email": email,
        "password_hash": hashed,
        "created_at": now,
        "plan": "free"
    }

    result = await mongo_manager.db["users"].insert_one(user_doc)
    user_id = str(result.inserted_id)

    # Initialize Researcher Node in Knowledge Graph (Phase 3 requirement)
    try:
        from app.memory.graph import create_researcher_node
        await create_researcher_node(user_id, email)
    except Exception as e:
        logger.warning(f"Failed to create researcher graph node on register: {e}")

    access_token = create_access_token({"sub": user_id, "email": email})
    refresh_token = create_refresh_token({"sub": user_id, "email": email})

    response.set_cookie(key="access_token", value=access_token, httponly=True, samesite="lax")

    return AuthResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=UserResponse(id=user_id, email=email, plan="free", created_at=now)
    )

@router.post("/login", response_model=AuthResponse)
async def login_user(body: UserLoginRequest, response: Response):
    email = body.email.lower().strip()
    if mongo_manager.db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection is not available."
        )

    user = await mongo_manager.db["users"].find_one({"email": email})
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password."
        )

    if not verify_password(body.password, user.get("password_hash", "")):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password."
        )

    user_id = str(user["_id"])
    access_token = create_access_token({"sub": user_id, "email": email})
    refresh_token = create_refresh_token({"sub": user_id, "email": email})

    response.set_cookie(key="access_token", value=access_token, httponly=True, samesite="lax")

    return AuthResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=UserResponse(
            id=user_id,
            email=email,
            plan=user.get("plan", "free"),
            created_at=user.get("created_at")
        )
    )

@router.post("/refresh")
async def refresh_access_token(body: TokenRefreshRequest, response: Response):
    payload = decode_token(body.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token."
        )

    user_id = payload.get("sub")
    email = payload.get("email")
    new_access_token = create_access_token({"sub": user_id, "email": email})

    response.set_cookie(key="access_token", value=new_access_token, httponly=True, samesite="lax")

    return {
        "access_token": new_access_token,
        "token_type": "bearer"
    }

@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie("access_token")
    return {"message": "Successfully logged out."}

@router.get("/me", response_model=UserResponse)
async def get_me(current_user: Dict[str, Any] = Depends(get_current_user)):
    return UserResponse(
        id=current_user["id"],
        email=current_user["email"],
        plan=current_user["plan"],
        created_at=current_user.get("created_at")
    )
