import pytest
from app.pipeline.planner import plan_query
from app.pipeline.retrieval import execute_retrieval

@pytest.mark.asyncio
async def test_planner_and_retrieval_end_to_end():
    question = "Does ibuprofen interact with lisinopril?"
    plan = await plan_query(question)
    results = await execute_retrieval(plan)
    
    assert isinstance(results, dict)
    assert "pubmed" in results
    assert "chembl" in results
    assert "pubchem" in results
    assert "drugbank" in results

    total_items = sum(len(v) for v in results.values())
    print(f"\n[Retrieval Test] Total items retrieved: {total_items}")
    for src, items in results.items():
        print(f" - {src}: {len(items)} items")

@pytest.mark.asyncio
async def test_retrieval_resilience_on_source_failure(monkeypatch):
    # Simulate PubMed throwing an exception
    async def mock_failing_pubmed(*args, **kwargs):
        raise RuntimeError("Simulated network timeout for PubMed")

    import app.sources.pubmed_client
    monkeypatch.setattr(app.sources.pubmed_client, "fetch_pubmed_results", mock_failing_pubmed)

    plan = {"sources": ["pubmed", "chembl"], "per_source_query": {"pubmed": "metformin", "chembl": "metformin"}}
    results = await execute_retrieval(plan)

    # PubMed should return [] due to graceful error handling, while ChEMBL succeeds
    assert results["pubmed"] == []
    assert len(results["chembl"]) > 0
    print("\n[Resilience Test] PubMed failed gracefully with [], ChEMBL succeeded.")
