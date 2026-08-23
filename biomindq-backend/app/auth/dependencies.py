import secrets
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timezone
from fastapi import Request, Response, HTTPException, status, Depends
from app.auth.security import decode_token
from app.db.mongo import mongo_manager

logger = logging.getLogger(__name__)

TRIAL_COOKIE_NAME = "bmq_trial_token"

async def get_current_user(request: Request) -> Dict[str, Any]:
    token = None
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
    elif "access_token" in request.cookies:
        token = request.cookies.get("access_token")

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials were not provided."
        )

    payload = decode_token(token)
    if not payload or payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token."
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token payload missing subject identifier."
        )

    if mongo_manager.db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database service unavailable."
        )

    from bson import ObjectId
    try:
        user = await mongo_manager.db["users"].find_one({"_id": ObjectId(user_id)})
    except Exception:
        user = await mongo_manager.db["users"].find_one({"_id": user_id})

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User associated with token not found."
        )

    user_data = {
        "id": str(user["_id"]),
        "email": user.get("email"),
        "plan": user.get("plan", "free"),
        "created_at": user.get("created_at")
    }
    return user_data

async def get_optional_user(request: Request) -> Optional[Dict[str, Any]]:
    try:
        return await get_current_user(request)
    except HTTPException:
        return None

async def verify_trial_or_auth(request: Request, response: Response) -> Dict[str, Any]:
    user = await get_optional_user(request)
    if user:
        return {"user": user, "is_authenticated": True, "trial_token": None}

    # Anonymous Trial Gate
    trial_token = request.cookies.get(TRIAL_COOKIE_NAME)
    if not trial_token:
        trial_token = secrets.token_hex(16)

    usage_count = 0
    if mongo_manager.db is not None:
        try:
            record = await mongo_manager.db["trial_usage"].find_one({"trial_token": trial_token})
            if record:
                usage_count = record.get("count", 0)
        except Exception as e:
            logger.warning(f"Error checking trial usage in MongoDB: {e}")

    if usage_count >= 1:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "message": "Trial query limit reached. Sign up to continue.",
                "trial_limit_reached": True
            }
        )

    response.set_cookie(
        key=TRIAL_COOKIE_NAME,
        value=trial_token,
        httponly=True,
        max_age=60 * 60 * 24 * 30, # 30 days
        samesite="lax"
    )

    await record_trial_usage(trial_token)

    return {"user": None, "is_authenticated": False, "trial_token": trial_token}

async def record_trial_usage(trial_token: str):
    if not trial_token or mongo_manager.db is None:
        return
    try:
        now = datetime.now(timezone.utc)
        await mongo_manager.db["trial_usage"].update_one(
            {"trial_token": trial_token},
            {"$inc": {"count": 1}, "$set": {"last_used_at": now}},
            upsert=True
        )
    except Exception as e:
        logger.error(f"Failed to record trial usage: {e}")
