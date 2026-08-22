import logging
from typing import List, Dict, Any, Optional
import httpx

logger = logging.getLogger(__name__)

CHEMBL_BASE_URL = "https://www.ebi.ac.uk/chembl/api/data"

async def fetch_chembl_results(query: str, http_client: Optional[httpx.AsyncClient] = None, max_results: int = 5) -> List[Dict[str, Any]]:
    client = http_client or httpx.AsyncClient(timeout=8.0, follow_redirects=True)
    should_close = http_client is None

    results: List[Dict[str, Any]] = []
    try:
        url = f"{CHEMBL_BASE_URL}/molecule/search.json"
        params = {"q": query, "limit": max_results}
        
        resp = await client.get(url, params=params)
        
        # Retry once if ChEMBL server returns 500 transient error
        if resp.status_code >= 500:
            logger.warning(f"ChEMBL returned HTTP {resp.status_code}, retrying after 0.5s...")
            import asyncio
            await asyncio.sleep(0.5)
            resp = await client.get(url, params=params)

        if resp.status_code == 200:
            data = resp.json()
            molecules = data.get("molecules", [])
            for mol in molecules:
                chembl_id = mol.get("molecule_chembl_id", "")
                pref_name = mol.get("pref_name") or chembl_id
                mol_type = mol.get("molecule_type", "Small molecule")
                max_phase = mol.get("max_phase", "0")

                struct = mol.get("molecule_structures") or {}
                smiles = struct.get("canonical_smiles", "")

                summary_parts = [f"Molecule Type: {mol_type}", f"Max Clinical Phase: {max_phase}"]
                if smiles:
                    summary_parts.append(f"SMILES: {smiles[:60]}...")
                
                results.append({
                    "id": chembl_id,
                    "title": f"{pref_name} ({chembl_id})",
                    "summary": " | ".join(summary_parts),
                    "url": f"https://www.ebi.ac.uk/chembl/compound_report_card/{chembl_id}/",
                    "source": "chembl"
                })
        else:
            logger.warning(f"ChEMBL query returned status code {resp.status_code}")

    except Exception as e:
        logger.error(f"ChEMBL client error fetching query '{query}': {e}")
    finally:
        if should_close:
            await client.aclose()

    return results
