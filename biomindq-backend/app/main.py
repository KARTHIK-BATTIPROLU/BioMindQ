import os
import logging
from contextlib import asynccontextmanager
import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.db.mongo import connect_to_mongo, close_mongo_connection
from app.api.routes_query import router as query_router
from app.api.routes_auth import router as auth_router
from app.api.routes_sessions import router as sessions_router
from app.api.routes_graph import router as graph_router

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
app.include_router(auth_router)
app.include_router(sessions_router)
app.include_router(graph_router)

static_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "static"))
index_path = os.path.join(static_dir, "index.html")

# Directly serve index.html at root / and /chat
@app.get("/", include_in_schema=False)
@app.get("/chat", include_in_schema=False)
async def serve_chatbot_ui():
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "BioMindQ API is running. Chatbot UI index.html not found."}

if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir, html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 3001))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=True)
