import pytest
from app.sources.pubmed_client import fetch_pubmed_results
from app.sources.chembl_client import fetch_chembl_results
from app.sources.pubchem_client import fetch_pubchem_results
from app.sources.drugbank_client import fetch_drugbank_results

@pytest.mark.asyncio
async def test_pubmed_client():
    results = await fetch_pubmed_results("metformin")
    assert isinstance(results, list)
    assert len(results) > 0, "PubMed should return results for 'metformin'"
    first = results[0]
    assert first["source"] == "pubmed"
    assert "id" in first
    assert "title" in first
    assert "summary" in first
    assert "url" in first
    print(f"\n[PubMed Result] Title: {first['title']} | URL: {first['url']}")

@pytest.mark.asyncio
async def test_chembl_client():
    results = await fetch_chembl_results("metformin")
    assert isinstance(results, list)
    assert len(results) > 0, "ChEMBL should return results for 'metformin'"
    first = results[0]
    assert first["source"] == "chembl"
    assert "CHEMBL" in first["id"]
    assert "url" in first
    print(f"\n[ChEMBL Result] ID: {first['id']} | Title: {first['title']}")

@pytest.mark.asyncio
async def test_pubchem_client():
    results = await fetch_pubchem_results("metformin")
    assert isinstance(results, list)
    assert len(results) > 0, "PubChem should return results for 'metformin'"
    first = results[0]
    assert first["source"] == "pubchem"
    assert "CID_" in first["id"]
    assert "url" in first
    print(f"\n[PubChem Result] ID: {first['id']} | Title: {first['title']}")

@pytest.mark.asyncio
async def test_drugbank_client_gated():
    # Without DRUGBANK_API_KEY set, it must return [] immediately without crashing
    results = await fetch_drugbank_results("metformin")
    assert isinstance(results, list)
    assert len(results) == 0, "DrugBank client without API key should return []"
    print("\n[DrugBank Gated] Successfully returned [] when API key is unconfigured.")
