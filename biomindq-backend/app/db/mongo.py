import logging
from typing import Optional, Dict, Any
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from app.config import settings

logger = logging.getLogger(__name__)

class MongoDBManager:
    client: Optional[AsyncIOMotorClient] = None
    db: Optional[AsyncIOMotorDatabase] = None

mongo_manager = MongoDBManager()

async def connect_to_mongo():
    try:
        if settings.MONGODB_URI:
            mongo_manager.client = AsyncIOMotorClient(
                settings.MONGODB_URI,
                serverSelectionTimeoutMS=2000
            )
            mongo_manager.db = mongo_manager.client[settings.MONGODB_DB_NAME]
            # Quick ping test
            await mongo_manager.client.admin.command('ping')
            logger.info("Connected to MongoDB successfully.")
    except Exception as e:
        logger.warning(f"MongoDB connection warning: {e}")
        mongo_manager.client = None
        mongo_manager.db = None

async def close_mongo_connection():
    if mongo_manager.client:
        mongo_manager.client.close()
        logger.info("MongoDB client connection closed.")

async def check_mongo_health() -> str:
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
            logger.error(f"Failed to save query record to MongoDB: {e}")
            return None
    return None
