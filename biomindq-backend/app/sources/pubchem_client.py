import logging
from typing import List, Dict, Any, Optional
import httpx

logger = logging.getLogger(__name__)

PUBCHEM_BASE_URL = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"

async def fetch_pubchem_results(query: str, http_client: Optional[httpx.AsyncClient] = None, max_results: int = 5) -> List[Dict[str, Any]]:
    client = http_client or httpx.AsyncClient(timeout=8.0, follow_redirects=True)
    should_close = http_client is None

    results: List[Dict[str, Any]] = []
    try:
        # Step 1: Query compound description by name
        url = f"{PUBCHEM_BASE_URL}/compound/name/{query}/description/JSON"
        resp = await client.get(url)
        
        if resp.status_code == 200:
            data = resp.json()
            descriptions = data.get("InformationList", {}).get("Information", [])
            for info in descriptions[:max_results]:
                cid = info.get("CID")
                title = info.get("Title") or f"PubChem Compound {cid}"
                description = info.get("Description") or info.get("Comment") or "PubChem chemical compound entry."
                
                if cid:
                    results.append({
                        "id": f"CID_{cid}",
                        "title": title,
                        "summary": description[:250] + ("..." if len(description) > 250 else ""),
                        "url": f"https://pubchem.ncbi.nlm.nih.gov/compound/{cid}",
                        "source": "pubchem"
                    })
        elif resp.status_code == 404:
            # Fallback search by CIDs if direct description name lookup fails
            cid_url = f"{PUBCHEM_BASE_URL}/compound/name/{query}/cids/JSON"
            cid_resp = await client.get(cid_url)
            if cid_resp.status_code == 200:
                cid_data = cid_resp.json()
                cids = cid_data.get("IdentifierList", {}).get("CID", [])
                for cid in cids[:max_results]:
                    results.append({
                        "id": f"CID_{cid}",
                        "title": f"Compound CID {cid} ({query})",
                        "summary": f"PubChem chemical record for search term '{query}'. CID: {cid}.",
                        "url": f"https://pubchem.ncbi.nlm.nih.gov/compound/{cid}",
                        "source": "pubchem"
                    })
    except Exception as e:
        logger.error(f"PubChem client error fetching query '{query}': {e}")
    finally:
        if should_close:
            await client.aclose()

    return results
