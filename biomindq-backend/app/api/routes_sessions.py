import logging
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, status, Query
from bson import ObjectId
from app.auth.dependencies import get_current_user
from app.db.mongo import mongo_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/sessions", tags=["sessions"])

@router.get("")
async def list_user_sessions(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=50),
    topic: Optional[str] = None,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    if mongo_manager.db is None:
        raise HTTPException(status_code=503, detail="Database unavailable")

    user_id = current_user["id"]
    skip = (page - 1) * limit

    filter_query: Dict[str, Any] = {"user_id": user_id}
    if topic:
        filter_query["topics"] = topic.lower().strip()

    cursor = mongo_manager.db["sessions"].find(filter_query).sort("created_at", -1).skip(skip).limit(limit)
    sessions = []
    async for doc in cursor:
        sessions.append({
            "id": str(doc["_id"]),
            "user_id": doc.get("user_id"),
            "query_text": doc.get("query_text"),
            "topics": doc.get("topics", []),
            "created_at": doc.get("created_at"),
            "confidence_score": doc.get("answer_payload", {}).get("consensus", {}).get("confidence_score") or doc.get("answer_payload", {}).get("final_answer", {}).get("confidence_score")
        })

    total = await mongo_manager.db["sessions"].count_documents(filter_query)

    return {
        "sessions": sessions,
        "page": page,
        "limit": limit,
        "total": total,
        "has_more": (skip + len(sessions)) < total
    }

@router.get("/{session_id}")
async def get_session_detail(
    session_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    if mongo_manager.db is None:
        raise HTTPException(status_code=503, detail="Database unavailable")

    user_id = current_user["id"]
    try:
        query_id = ObjectId(session_id)
    except Exception:
        query_id = session_id

    doc = await mongo_manager.db["sessions"].find_one({"_id": query_id, "user_id": user_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Session not found or access denied.")

    return {
        "id": str(doc["_id"]),
        "user_id": doc.get("user_id"),
        "query_text": doc.get("query_text"),
        "created_at": doc.get("created_at"),
        "topics": doc.get("topics", []),
        "answer_payload": doc.get("answer_payload", {})
    }

@router.delete("/{session_id}")
async def delete_session(
    session_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    if mongo_manager.db is None:
        raise HTTPException(status_code=503, detail="Database unavailable")

    user_id = current_user["id"]
    try:
        query_id = ObjectId(session_id)
    except Exception:
        query_id = session_id

    result = await mongo_manager.db["sessions"].delete_one({"_id": query_id, "user_id": user_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Session not found or access denied.")

    return {"message": "Session deleted successfully."}
