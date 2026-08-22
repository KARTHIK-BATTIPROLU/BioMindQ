import os
import logging
from contextlib import asynccontextmanager
import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.db.mongo import connect_to_mongo, close_mongo_connection
from app.api.routes_query import router as query_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("biomindq")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing shared httpx.AsyncClient...")
    app.state.http_client = httpx.AsyncClient(timeout=10.0, follow_redirects=True)
    
    await connect_to_mongo()
    
    yield
    
    logger.info("Closing shared httpx.AsyncClient...")
    await app.state.http_client.aclose()
    await close_mongo_connection()

app = FastAPI(
    title="BioMindQ Research Intelligence API",
    description="Multi-Source Biomedical Evidence Verification Engine Backend",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(query_router)

# Mount static Chatbot UI at /chat
static_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "static"))
if os.path.exists(static_dir):
    app.mount("/chat", StaticFiles(directory=static_dir, html=True), name="chat")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=3000, reload=True)
