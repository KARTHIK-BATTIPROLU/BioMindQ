import pytest
from app.models.schemas import QueryRequest, QueryResponse
from app.pipeline.consensus import compute_consensus_meter

@pytest.mark.asyncio
async def test_consensus_and_citation_tagging_integration():
    sample_stances = [
        {"item_id": "pm_1", "source": "pubmed", "stance": "supports"},
        {"item_id": "cm_1", "source": "chembl", "stance": "contradicts"},
        {"item_id": "pc_1", "source": "pubchem", "stance": "mentions"}
    ]
    
    consensus = compute_consensus_meter(sample_stances)
    assert consensus["label"] == "Mixed Evidence"
    assert consensus["supports"] == 1
    assert consensus["contradicts"] == 1
    assert consensus["mentions"] == 1
    assert consensus["total_sources"] == 3
