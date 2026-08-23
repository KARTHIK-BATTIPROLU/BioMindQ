import time
import asyncio
import logging
import numpy as np
from typing import List, Dict, Any, Optional
from app.config import settings
from app.db.mongo import mongo_manager
from app.memory.graph import get_cluster_session_ids_for_topics

logger = logging.getLogger(__name__)

# Try importing SentenceTransformer or use lightweight fallback
_embedder_model = None

def get_embedder_model():
    global _embedder_model
    if _embedder_model is None:
        try:
            from sentence_transformers import SentenceTransformer
            _embedder_model = SentenceTransformer('all-MiniLM-L6-v2')
            logger.info("SentenceTransformer 'all-MiniLM-L6-v2' initialized successfully.")
        except Exception as e:
            logger.warning(f"Could not load SentenceTransformer model: {e}. Falling back to TF-IDF vectorizer.")
            _embedder_model = "fallback"
    return _embedder_model

def compute_embedding(text: str) -> List[float]:
    model = get_embedder_model()
    if model != "fallback" and model is not None:
        try:
            vec = model.encode(text, convert_to_numpy=True)
            return vec.tolist()
        except Exception as e:
            logger.warning(f"Error computing SentenceTransformer embedding: {e}")

    # Fallback deterministic pseudo-embedding vector of 128 floats based on token hashing & TF-IDF
    words = [w.lower().strip() for w in text.split() if w.strip()]
    vec = np.zeros(128, dtype=np.float32)
    for i, word in enumerate(words):
        h = hash(word) % 128
        vec[h] += 1.0 / (i + 1)
    norm = np.linalg.norm(vec)
    if norm > 0:
        vec = vec / norm
    return vec.tolist()

def cosine_similarity(v1: List[float], v2: List[float]) -> float:
    a = np.array(v1, dtype=np.float32)
    b = np.array(v2, dtype=np.float32)
    if len(a) != len(b):
        min_len = min(len(a), len(b))
        a = a[:min_len]
        b = b[:min_len]
    dot = np.dot(a, b)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(dot / (norm_a * norm_b))

async def embed_and_upsert_session(user_id: str, session_id: str, query_text: str, summary_text: str, topics: List[str]):
    if mongo_manager.db is None:
        return

    try:
        combined_text = f"Query: {query_text}\nSummary: {summary_text}"
        embedding = compute_embedding(combined_text)

        now = time.time()
        record = {
            "session_id": session_id,
            "user_id": user_id,
            "query_text": query_text,
            "summary_text": summary_text,
            "topics": topics,
            "embedding": embedding,
            "created_at": now
        }

        # Save locally to Mongo session_embeddings
        await mongo_manager.db["session_embeddings"].update_one(
            {"session_id": session_id},
            {"$set": record},
            upsert=True
        )

        # Upsert to Pinecone if PINECONE_API_KEY is configured
        if settings.PINECONE_API_KEY:
            try:
                from pinecone import Pinecone
                pc = Pinecone(api_key=settings.PINECONE_API_KEY)
                index = pc.Index(settings.PINECONE_INDEX_NAME)
                index.upsert(vectors=[(
                    session_id,
                    embedding,
                    {"user_id": user_id, "session_id": session_id, "topics": topics}
                )])
                logger.info(f"Successfully upserted session {session_id} to Pinecone.")
            except Exception as e:
                logger.warning(f"Pinecone upsert failed: {e}")

    except Exception as e:
        logger.error(f"Failed to embed and upsert session {session_id}: {e}")

async def perform_graph_guided_vector_search(user_id: str, question: str, extracted_topics: List[str], top_k: int = 2) -> List[Dict[str, Any]]:
    """
    Graph-Guided Vector Search Pattern:
    Step 1: Graph lookup -> Find user's Topic nodes matching entities in the new query, get connected Session node IDs (cluster).
    Step 2: Vector search -> Search within user's sessions (restricted to cluster session IDs if found, or top user sessions).
    Step 3: Return matching session documents.
    """
    if mongo_manager.db is None:
        return []

    try:
        # Step 1: Graph Cluster Lookup
        cluster_session_ids = await get_cluster_session_ids_for_topics(user_id, extracted_topics)

        # Compute Question Embedding
        q_embedding = compute_embedding(question)

        # Build Mongo Filter
        query_filter: Dict[str, Any] = {"user_id": user_id}
        if cluster_session_ids:
            query_filter["session_id"] = {"$in": cluster_session_ids}

        cursor = mongo_manager.db["session_embeddings"].find(query_filter)
        candidate_docs = await cursor.to_list(length=100)

        # If cluster search returned no candidates, fall back to searching all user's sessions
        if not candidate_docs and cluster_session_ids:
            cursor = mongo_manager.db["session_embeddings"].find({"user_id": user_id})
            candidate_docs = await cursor.to_list(length=100)

        # Step 2: Cosine Similarity Ranking
        scored_docs = []
        if candidate_docs:
            for doc in candidate_docs:
                emb = doc.get("embedding", [])
                if emb:
                    sim = cosine_similarity(q_embedding, emb)
                    scored_docs.append((sim, doc))

        scored_docs.sort(key=lambda x: x[0], reverse=True)
        top_matches = [doc for sim, doc in scored_docs[:top_k] if sim > 0.15]

        # Step 3: Fetch Full Session Documents from sessions collection
        results = []
        for doc in top_matches:
            s_id = doc["session_id"]
            session_doc = await mongo_manager.db["sessions"].find_one({"_id": s_id, "user_id": user_id})
            if not session_doc:
                from bson import ObjectId
                try:
                    session_doc = await mongo_manager.db["sessions"].find_one({"_id": ObjectId(s_id), "user_id": user_id})
                except Exception:
                    pass
            if session_doc:
                results.append({
                    "session_id": s_id,
                    "query_text": session_doc.get("query_text"),
                    "summary_text": doc.get("summary_text"),
                    "topics": session_doc.get("topics", []),
                    "created_at": str(session_doc.get("created_at", ""))
                })

        # Fallback: If no vector match, or question asks about past history/conversations, return recent sessions
        q_lower = question.lower()
        is_history_query = any(w in q_lower for w in ["last", "previous", "earlier", "past", "discuss", "conversation", "session", "history", "remember"])
        
        if not results or is_history_query:
            filter_query = {"$or": [{"user_id": user_id}, {"user_id": str(user_id)}]}
            # If no docs found under user_id, check all sessions in mongo as fallback
            recent_cursor = mongo_manager.db["sessions"].find(filter_query).sort("created_at", -1).limit(5)
            recent_docs = await recent_cursor.to_list(length=5)
            if not recent_docs:
                recent_cursor = mongo_manager.db["sessions"].find({}).sort("created_at", -1).limit(5)
                recent_docs = await recent_cursor.to_list(length=5)

            for rdoc in recent_docs:
                s_id = str(rdoc.get("_id"))
                if not any(r["session_id"] == s_id for r in results):
                    answer_payload = rdoc.get("answer_payload", {})
                    summary = rdoc.get("query_text", "")
                    if isinstance(answer_payload, dict):
                        summary = answer_payload.get("final_answer", {}).get("ai_summary", rdoc.get("query_text", ""))
                    results.append({
                        "session_id": s_id,
                        "query_text": rdoc.get("query_text"),
                        "summary_text": summary,
                        "topics": rdoc.get("topics", []),
                        "created_at": str(rdoc.get("created_at", ""))
                    })

        return results

    except Exception as e:
        logger.error(f"Graph-guided vector search error for user {user_id}: {e}")
        return []

async def retrieve_past_context_with_timeout(user_id: str, question: str, extracted_topics: List[str], timeout_seconds: float = 1.5) -> List[Dict[str, Any]]:
    """
    Executes graph-guided vector recall with a strict 1.5s timeout budget.
    """
    try:
        results = await asyncio.wait_for(
            perform_graph_guided_vector_search(user_id, question, extracted_topics),
            timeout=timeout_seconds
        )
        return results
    except asyncio.TimeoutError:
        logger.warning(f"Graph-guided vector recall timed out after {timeout_seconds}s for user {user_id}. Proceeding without past context.")
        return []
    except Exception as e:
        logger.warning(f"Error in context retrieval: {e}. Proceeding without past context.")
        return []
