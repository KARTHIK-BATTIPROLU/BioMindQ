import asyncio
import time
import logging
from typing import Dict, Any, List, Optional
import httpx
from app.sources.pubmed_client import fetch_pubmed_results
from app.sources.chembl_client import fetch_chembl_results
from app.sources.pubchem_client import fetch_pubchem_results
from app.sources.drugbank_client import fetch_drugbank_results
from app.db.mongo import log_source_health

logger = logging.getLogger(__name__)

def get_source_client(source: str):
    import app.sources.pubmed_client as pm
    import app.sources.chembl_client as cm
    import app.sources.pubchem_client as pc
    import app.sources.drugbank_client as db
    
    mapping = {
        "pubmed": pm.fetch_pubmed_results,
        "chembl": cm.fetch_chembl_results,
        "pubchem": pc.fetch_pubchem_results,
        "drugbank": db.fetch_drugbank_results,
    }
    return mapping.get(source)

async def fetch_single_source(source: str, query: str, http_client: Optional[httpx.AsyncClient]) -> List[Dict[str, Any]]:
    client_func = get_source_client(source)
    if not client_func:
        logger.warning(f"Unknown source '{source}' requested; skipping.")
        return []

    start_time = time.time()
    success = False
    error_msg = None
    results: List[Dict[str, Any]] = []

    try:
        results = await client_func(query, http_client=http_client)
        success = True
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Error fetching from source '{source}': {e}")
        results = []
    finally:
        latency_ms = (time.time() - start_time) * 1000.0
        # Log latency and success to source_health collection asynchronously
        asyncio.create_task(log_source_health(source, success, latency_ms, error_msg))

    return results

async def execute_retrieval(plan: Dict[str, Any], http_client: Optional[httpx.AsyncClient] = None) -> Dict[str, List[Dict[str, Any]]]:
    sources: List[str] = plan.get("sources", [])
    per_source_query: Dict[str, str] = plan.get("per_source_query", {})

    raw_results: Dict[str, List[Dict[str, Any]]] = {
        "pubmed": [],
        "chembl": [],
        "pubchem": [],
        "drugbank": []
    }

    if not sources:
        return raw_results

    tasks = []
    task_sources = []

    for src in sources:
        if get_source_client(src):
            query = per_source_query.get(src, "")
            tasks.append(fetch_single_source(src, query, http_client))
            task_sources.append(src)

    if tasks:
        gathered_results = await asyncio.gather(*tasks, return_exceptions=True)

        for src, res in zip(task_sources, gathered_results):
            if isinstance(res, Exception):
                logger.error(f"Concurrent retrieval exception for '{src}': {res}")
                raw_results[src] = []
            else:
                raw_results[src] = res or []

    return raw_results
