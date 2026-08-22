import logging
from typing import List, Dict, Any, Optional
import httpx
from app.config import settings

logger = logging.getLogger(__name__)

NCBI_BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

async def fetch_pubmed_results(query: str, http_client: Optional[httpx.AsyncClient] = None, max_results: int = 5) -> List[Dict[str, Any]]:
    client = http_client or httpx.AsyncClient(timeout=8.0, follow_redirects=True)
    should_close = http_client is None

    results: List[Dict[str, Any]] = []
    try:
        # Step 1: E-Search for ID list
        search_params = {
            "db": "pubmed",
            "term": query,
            "retmode": "json",
            "retmax": max_results
        }
        if settings.NCBI_API_KEY:
            search_params["api_key"] = settings.NCBI_API_KEY

        search_resp = await client.get(f"{NCBI_BASE_URL}/esearch.fcgi", params=search_params)
        search_resp.raise_for_status()
        search_data = search_resp.json()
        
        id_list = search_data.get("esearchresult", {}).get("idlist", [])
        if not id_list:
            return []

        # Step 2: E-Summary for details
        summary_params = {
            "db": "pubmed",
            "id": ",".join(id_list),
            "retmode": "json"
        }
        if settings.NCBI_API_KEY:
            summary_params["api_key"] = settings.NCBI_API_KEY

        summary_resp = await client.get(f"{NCBI_BASE_URL}/esummary.fcgi", params=summary_params)
        summary_resp.raise_for_status()
        summary_data = summary_resp.json().get("result", {})

        for pmid in id_list:
            item = summary_data.get(str(pmid), {})
            title = item.get("title", f"PubMed Article {pmid}")
            # Format source authors / journal / pubdate as summary
            pubdate = item.get("pubdate", "")
            source_journal = item.get("source", "")
            authors = [a.get("name", "") for a in item.get("authors", [])[:3]]
            author_str = ", ".join(authors) + (" et al." if len(item.get("authors", [])) > 3 else "")
            
            summary_text = f"Published in {source_journal} ({pubdate}). Authors: {author_str}" if source_journal else f"PubMed Abstract PMID:{pmid}"
            
            results.append({
                "id": str(pmid),
                "title": title.rstrip('.'),
                "summary": summary_text,
                "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                "source": "pubmed"
            })
    except Exception as e:
        logger.error(f"PubMed client error fetching query '{query}': {e}")
    finally:
        if should_close:
            await client.aclose()

    return results
