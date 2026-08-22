import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from app.db.mongo import mongo_manager

logger = logging.getLogger(__name__)

async def create_researcher_node(user_id: str, email: str):
    if mongo_manager.db is None:
        return
    try:
        now = datetime.now(timezone.utc)
        node_id = f"researcher_{user_id}"
        await mongo_manager.db["graph_nodes"].update_one(
            {"node_id": node_id},
            {
                "$set": {
                    "node_id": node_id,
                    "user_id": user_id,
                    "type": "Researcher",
                    "name": email,
                    "normalized_name": email.lower(),
                    "updated_at": now
                },
                "$setOnInsert": {"created_at": now}
            },
            upsert=True
        )
    except Exception as e:
        logger.error(f"Failed to create/update researcher graph node: {e}")

async def upsert_session_graph(user_id: str, session_id: str, query_text: str, topics: List[str]):
    if mongo_manager.db is None:
        return

    try:
        now = datetime.now(timezone.utc)
        researcher_node_id = f"researcher_{user_id}"

        # 1. Ensure Researcher Node
        user = await mongo_manager.db["users"].find_one({"_id": user_id})
        email = user.get("email", user_id) if user else user_id
        await create_researcher_node(user_id, email)

        # 2. Create Session Node
        session_node_id = f"session_{session_id}"
        session_snippet = query_text[:40] + ("..." if len(query_text) > 40 else "")
        await mongo_manager.db["graph_nodes"].update_one(
            {"node_id": session_node_id},
            {
                "$set": {
                    "node_id": session_node_id,
                    "user_id": user_id,
                    "type": "Session",
                    "name": session_snippet,
                    "session_id": session_id,
                    "query_text": query_text,
                    "updated_at": now
                },
                "$setOnInsert": {"created_at": now}
            },
            upsert=True
        )

        # 3. Create HAS_SESSION Edge (Researcher -> Session)
        edge_rs_id = f"edge_{researcher_node_id}_{session_node_id}"
        await mongo_manager.db["graph_edges"].update_one(
            {"edge_id": edge_rs_id},
            {
                "$set": {
                    "edge_id": edge_rs_id,
                    "user_id": user_id,
                    "from_node_id": researcher_node_id,
                    "to_node_id": session_node_id,
                    "type": "HAS_SESSION",
                    "updated_at": now
                },
                "$setOnInsert": {"created_at": now}
            },
            upsert=True
        )

        # 4. Upsert Topic Nodes & MENTIONS Edges
        for topic in topics:
            raw_name = topic.strip()
            if not raw_name:
                continue
            norm_name = raw_name.lower()
            topic_node_id = f"topic_{user_id}_{norm_name}"

            # MERGE-style upsert for Topic Node (deduped by normalized_name per user)
            await mongo_manager.db["graph_nodes"].update_one(
                {"node_id": topic_node_id},
                {
                    "$set": {
                        "node_id": topic_node_id,
                        "user_id": user_id,
                        "type": "Topic",
                        "name": raw_name,
                        "normalized_name": norm_name,
                        "updated_at": now
                    },
                    "$setOnInsert": {"created_at": now}
                },
                upsert=True
            )

            # Create MENTIONS Edge (Session -> Topic)
            edge_st_id = f"edge_{session_node_id}_{topic_node_id}"
            await mongo_manager.db["graph_edges"].update_one(
                {"edge_id": edge_st_id},
                {
                    "$set": {
                        "edge_id": edge_st_id,
                        "user_id": user_id,
                        "from_node_id": session_node_id,
                        "to_node_id": topic_node_id,
                        "type": "MENTIONS",
                        "updated_at": now
                    },
                    "$setOnInsert": {"created_at": now}
                },
                upsert=True
            )

    except Exception as e:
        logger.error(f"Failed to upsert session graph for session {session_id}: {e}")

async def get_user_graph(user_id: str) -> Dict[str, Any]:
    if mongo_manager.db is None:
        return {"nodes": [], "edges": []}

    try:
        nodes_cursor = mongo_manager.db["graph_nodes"].find({"user_id": user_id})
        nodes = []
        async for n in nodes_cursor:
            nodes.append({
                "id": n["node_id"],
                "type": n.get("type"),
                "name": n.get("name"),
                "normalized_name": n.get("normalized_name"),
                "session_id": n.get("session_id"),
                "query_text": n.get("query_text")
            })

        edges_cursor = mongo_manager.db["graph_edges"].find({"user_id": user_id})
        edges = []
        async for e in edges_cursor:
            edges.append({
                "id": e["edge_id"],
                "source": e.get("from_node_id"),
                "target": e.get("to_node_id"),
                "type": e.get("type")
            })

        return {"nodes": nodes, "edges": edges}

    except Exception as e:
        logger.error(f"Failed to fetch user graph for {user_id}: {e}")
        return {"nodes": [], "edges": []}

async def get_cluster_session_ids_for_topics(user_id: str, topic_names: List[str]) -> List[str]:
    if mongo_manager.db is None or not topic_names:
        return []

    try:
        norm_topics = [t.lower().strip() for t in topic_names if t.strip()]
        topic_nodes = await mongo_manager.db["graph_nodes"].find({
            "user_id": user_id,
            "type": "Topic",
            "normalized_name": {"$in": norm_topics}
        }).to_list(length=100)

        topic_node_ids = [tn["node_id"] for tn in topic_nodes]
        if not topic_node_ids:
            return []

        # Find MENTIONS edges targeting these topics
        mentions_edges = await mongo_manager.db["graph_edges"].find({
            "user_id": user_id,
            "type": "MENTIONS",
            "to_node_id": {"$in": topic_node_ids}
        }).to_list(length=200)

        session_node_ids = set([e["from_node_id"] for e in mentions_edges])
        session_ids = [sn.replace("session_", "") for sn in session_node_ids if sn.startswith("session_")]
        return session_ids

    except Exception as e:
        logger.error(f"Failed to get cluster session IDs for topics: {e}")
        return []
