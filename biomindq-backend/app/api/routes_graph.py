import logging
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, Depends
from app.auth.dependencies import get_current_user
from app.memory.graph import get_user_graph

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/graph", tags=["graph"])

@router.get("/user")
async def get_current_user_research_map(
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    user_id = current_user["id"]
    graph_data = await get_user_graph(user_id)
    return graph_data
