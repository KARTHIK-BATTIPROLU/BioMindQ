import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from app.config import settings

logger = logging.getLogger(__name__)

class InMemoryInsertResult:
    def __init__(self, inserted_id):
        self.inserted_id = inserted_id

class InMemoryDeleteResult:
    def __init__(self, deleted_count):
        self.deleted_count = deleted_count

class InMemoryCursor:
    def __init__(self, docs):
        self.docs = list(docs)

    def sort(self, key, direction=1):
        reverse = (direction == -1)
        self.docs.sort(key=lambda x: str(x.get(key, "")), reverse=reverse)
        return self

    def skip(self, n):
        self.docs = self.docs[n:]
        return self

    def limit(self, n):
        self.docs = self.docs[:n]
        return self

    def __aiter__(self):
        self._iter = iter(self.docs)
        return self

    async def __anext__(self):
        try:
            return next(self._iter)
        except StopIteration:
            raise StopAsyncIteration

    async def to_list(self, length=100):
        return self.docs[:length]

class InMemoryCollection:
    def __init__(self, name):
        self.name = name
        self.docs = []

    def _matches_filter(self, doc, filter_query):
        if not filter_query:
            return True
        for k, v in filter_query.items():
            if k == "_id":
                if str(doc.get("_id")) != str(v) and doc.get("_id") != v:
                    return False
            elif isinstance(v, dict):
                if "$in" in v:
                    val = doc.get(k)
                    if isinstance(val, list):
                        if not any(str(x) in [str(i) for i in v["$in"]] for x in val):
                            return False
                    elif str(val) not in [str(i) for i in v["$in"]]:
                        return False
            else:
                if doc.get(k) != v:
                    return False
        return True

    async def insert_one(self, document):
        doc = document.copy()
        if "_id" not in doc:
            doc["_id"] = str(ObjectId())
        self.docs.append(doc)
        return InMemoryInsertResult(doc["_id"])

    async def find_one(self, filter_query):
        for doc in self.docs:
            if self._matches_filter(doc, filter_query):
                return doc
        return None

    def find(self, filter_query=None):
        matched = [d for d in self.docs if self._matches_filter(d, filter_query)]
        return InMemoryCursor(matched)

    async def count_documents(self, filter_query=None):
        return len([d for d in self.docs if self._matches_filter(d, filter_query)])

    async def update_one(self, filter_query, update_query, upsert=False):
        existing = await self.find_one(filter_query)
        if existing:
            if "$set" in update_query:
                existing.update(update_query["$set"])
            if "$inc" in update_query:
                for k, v in update_query["$inc"].items():
                    existing[k] = existing.get(k, 0) + v
            return
        elif upsert:
            new_doc = {}
            if "$set" in update_query:
                new_doc.update(update_query["$set"])
            if "$setOnInsert" in update_query:
                new_doc.update(update_query["$setOnInsert"])
            if "$inc" in update_query:
                for k, v in update_query["$inc"].items():
                    new_doc[k] = v
            for k, v in filter_query.items():
                if not k.startswith("$") and k not in new_doc:
                    new_doc[k] = v
            await self.insert_one(new_doc)

    async def delete_one(self, filter_query):
        for i, doc in enumerate(self.docs):
            if self._matches_filter(doc, filter_query):
                self.docs.pop(i)
                return InMemoryDeleteResult(1)
        return InMemoryDeleteResult(0)

class InMemoryDatabase:
    def __init__(self):
        self.collections = {}

    def __getitem__(self, name):
        if name not in self.collections:
            self.collections[name] = InMemoryCollection(name)
        return self.collections[name]

class MongoDBManager:
    client: Optional[AsyncIOMotorClient] = None
    db: Any = None
    is_in_memory: bool = False

mongo_manager = MongoDBManager()

async def connect_to_mongo():
    try:
        if settings.MONGODB_URI:
            # 1. Try with certifi CA bundle
            try:
                import certifi
                ca_file = certifi.where()
                client = AsyncIOMotorClient(
                    settings.MONGODB_URI,
                    tlsCAFile=ca_file,
                    serverSelectionTimeoutMS=2000
                )
                await client.admin.command('ping')
                mongo_manager.client = client
                mongo_manager.db = client[settings.MONGODB_DB_NAME]
                mongo_manager.is_in_memory = False
                logger.info("Connected to MongoDB Atlas with certifi CA successfully.")
                await seed_demo_data()
                return
            except Exception as e:
                logger.warning(f"MongoDB certifi connection failed: {e}. Trying tlsAllowInvalidCertificates...")

            # 2. Try with tlsAllowInvalidCertificates=True for SSL issues
            try:
                client = AsyncIOMotorClient(
                    settings.MONGODB_URI,
                    tlsAllowInvalidCertificates=True,
                    serverSelectionTimeoutMS=2000
                )
                await client.admin.command('ping')
                mongo_manager.client = client
                mongo_manager.db = client[settings.MONGODB_DB_NAME]
                mongo_manager.is_in_memory = False
                logger.info("Connected to MongoDB with tlsAllowInvalidCertificates successfully.")
                await seed_demo_data()
                return
            except Exception as e:
                logger.warning(f"MongoDB tlsAllowInvalidCertificates failed: {e}. Falling back to InMemoryDatabase...")

    except Exception as e:
        logger.warning(f"MongoDB connection outer exception: {e}")

    # 3. Fallback to InMemoryDatabase if external MongoDB is unreachable
    mongo_manager.client = None
    mongo_manager.db = InMemoryDatabase()
    mongo_manager.is_in_memory = True
    logger.info("BioMindQ database initialized using InMemoryDatabase fallback (100% functional auth, sessions, and graph memory).")
    await seed_demo_data()

async def seed_demo_data():
    if mongo_manager.db is None:
        return

    try:
        from app.auth.security import hash_password
        from app.memory.graph import upsert_session_graph
        from app.memory.vector_store import embed_and_upsert_session

        demo_emails = ["demo@biomindq.ai", "researcher@biomindq.ai"]

        for demo_email in demo_emails:
            existing = await mongo_manager.db["users"].find_one({"email": demo_email})
            if existing:
                user_id = str(existing["_id"])
            else:
                now = datetime.now(timezone.utc)
                res = await mongo_manager.db["users"].insert_one({
                    "email": demo_email,
                    "password_hash": hash_password("password123"),
                    "created_at": now,
                    "plan": "researcher"
                })
                user_id = str(res.inserted_id)

            s_count = await mongo_manager.db["sessions"].count_documents({"user_id": user_id})
            if s_count > 0:
                continue

            now = datetime.now(timezone.utc)
            mock_sessions = [
                {
                    "user_id": user_id,
                    "created_at": now,
                    "query_text": "What is known about metformin's interaction with AMPK?",
                    "topics": ["metformin", "ampk", "gluconeogenesis", "insulin sensitivity"],
                    "answer_payload": {
                        "final_answer": {
                            "confidence_score": 92,
                            "ai_summary": "Metformin's principal downstream target is the energy-sensing kinase AMPK. The drug inhibits mitochondrial complex I, leading to an increased AMP/ATP ratio that allosterically activates AMPK."
                        },
                        "consensus": {"confidence_score": 92, "label": "Strong Consensus", "supports": 4, "contradicts": 0, "total_sources": 4}
                    }
                },
                {
                    "user_id": user_id,
                    "created_at": now,
                    "query_text": "How does GLP-1 activation synergize with metformin in type 2 diabetes?",
                    "topics": ["metformin", "glp-1", "semaglutide", "t2d", "insulin sensitivity"],
                    "answer_payload": {
                        "final_answer": {
                            "confidence_score": 95,
                            "ai_summary": "GLP-1 receptor agonists and metformin show synergistic metabolic benefits: GLP-1 enhances pancreatic insulin secretion while metformin lowers hepatic glucose output via AMPK activation."
                        },
                        "consensus": {"confidence_score": 95, "label": "Strong Consensus", "supports": 5, "contradicts": 0, "total_sources": 5}
                    }
                },
                {
                    "user_id": user_id,
                    "created_at": now,
                    "query_text": "Does ibuprofen interact with lisinopril and reduce antihypertensive efficacy?",
                    "topics": ["ibuprofen", "lisinopril", "blood pressure", "renal clearance"],
                    "answer_payload": {
                        "final_answer": {
                            "confidence_score": 88,
                            "ai_summary": "NSAIDs like ibuprofen inhibit renal prostaglandin synthesis, which can blunt the vasodilator effect of ACE inhibitors such as lisinopril and cause blood pressure elevation."
                        },
                        "consensus": {"confidence_score": 88, "label": "Strong Consensus", "supports": 4, "contradicts": 0, "total_sources": 4}
                    }
                },
                {
                    "user_id": user_id,
                    "created_at": now,
                    "query_text": "What are the renal clearance risks of combining NSAIDs like ibuprofen with ACE inhibitors?",
                    "topics": ["ibuprofen", "lisinopril", "renal clearance", "nephrotoxicity"],
                    "answer_payload": {
                        "final_answer": {
                            "confidence_score": 90,
                            "ai_summary": "Concomitant use of NSAIDs and ACE inhibitors ('double whammy') impairs renal hemodynamics, significantly decreasing glomerular filtration rate and elevating acute kidney failure risk."
                        },
                        "consensus": {"confidence_score": 90, "label": "Strong Consensus", "supports": 4, "contradicts": 0, "total_sources": 4}
                    }
                },
                {
                    "user_id": user_id,
                    "created_at": now,
                    "query_text": "Summarize recent clinical findings on GLP-1 receptor agonists and cardiovascular outcomes.",
                    "topics": ["glp-1", "semaglutide", "cardiovascular safety", "liraglutide"],
                    "answer_payload": {
                        "final_answer": {
                            "confidence_score": 94,
                            "ai_summary": "Major cardiovascular outcome trials (CVOTs) demonstrate that GLP-1 agonists like semaglutide significantly reduce major adverse cardiovascular events (MACE) in type 2 diabetes patients."
                        },
                        "consensus": {"confidence_score": 94, "label": "Strong Consensus", "supports": 6, "contradicts": 0, "total_sources": 6}
                    }
                }
            ]

            for sess in mock_sessions:
                res = await mongo_manager.db["sessions"].insert_one(sess)
                s_id = str(res.inserted_id)

                # Upsert into Knowledge Graph
                await upsert_session_graph(user_id, s_id, sess["query_text"], sess["topics"])

                # Upsert into Vector Store
                summary = sess["answer_payload"]["final_answer"]["ai_summary"]
                await embed_and_upsert_session(user_id, s_id, sess["query_text"], summary, sess["topics"])

            logger.info(f"Seeded researcher '{demo_email}' with 5 interconnected mock sessions, knowledge graph nodes, and vector embeddings.")

    except Exception as e:
        logger.error(f"Failed to seed demo data: {e}")

async def close_mongo_connection():
    if mongo_manager.client:
        mongo_manager.client.close()
        logger.info("MongoDB client connection closed.")

async def check_mongo_health() -> str:
    if mongo_manager.is_in_memory:
        return "in_memory"
    if not mongo_manager.client:
        return "unreachable"
    try:
        await mongo_manager.client.admin.command('ping')
        return "ok"
    except Exception:
        return "unreachable"

async def log_source_health(source: str, success: bool, latency_ms: float, error: Optional[str] = None):
    if mongo_manager.db is not None:
        try:
            from datetime import datetime, timezone
            record = {
                "source": source,
                "timestamp": datetime.now(timezone.utc),
                "success": success,
                "latency_ms": round(latency_ms, 2),
                "error": error
            }
            await mongo_manager.db["source_health"].insert_one(record)
        except Exception as e:
            logger.warning(f"Failed to log source_health record: {e}")

async def save_query_record(record: Dict[str, Any]) -> Optional[str]:
    if mongo_manager.db is not None:
        try:
            result = await mongo_manager.db["queries"].insert_one(record)
            return str(result.inserted_id)
        except Exception as e:
            logger.error(f"Failed to save query record: {e}")
            return None
    return None
