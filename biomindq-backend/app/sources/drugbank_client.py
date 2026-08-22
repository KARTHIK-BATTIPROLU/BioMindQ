import logging
from typing import List, Dict, Any, Optional
import httpx
from app.config import settings

logger = logging.getLogger(__name__)

DRUGBANK_BASE_URL = "https://api.drugbank.com/v1"

async def fetch_drugbank_results(query: str, http_client: Optional[httpx.AsyncClient] = None, max_results: int = 5) -> List[Dict[str, Any]]:
    # Hard constraint gate: Return [] immediately if no DRUGBANK_API_KEY is present
    if not settings.DRUGBANK_API_KEY:
        logger.info("DrugBank API key not configured; returning empty list.")
        return []

    client = http_client or httpx.AsyncClient(timeout=8.0, follow_redirects=True)
    should_close = http_client is None

    results: List[Dict[str, Any]] = []
    try:
        headers = {
            "Authorization": f"Bearer {settings.DRUGBANK_API_KEY}",
            "Accept": "application/json"
        }
        url = f"{DRUGBANK_BASE_URL}/us/drugs/search"
        params = {"q": query, "limit": max_results}

        resp = await client.get(url, headers=headers, params=params)
        resp.raise_for_status()
        data = resp.json()

        drugs = data if isinstance(data, list) else data.get("drugs", [])
        for drug in drugs[:max_results]:
            drug_id = drug.get("drugbank_id") or drug.get("id", "")
            name = drug.get("name", f"DrugBank {drug_id}")
            description = drug.get("description") or drug.get("indication") or "DrugBank pharmaceutical entry."

            results.append({
                "id": drug_id,
                "title": f"{name} ({drug_id})",
                "summary": description[:250] + ("..." if len(description) > 250 else ""),
                "url": f"https://go.drugbank.com/drugs/{drug_id}",
                "source": "drugbank"
            })
    except Exception as e:
        logger.error(f"DrugBank client error fetching query '{query}': {e}")
    finally:
        if should_close:
            await client.aclose()

    return results
