import pytest
from app.pipeline.consensus import compute_consensus_meter

def test_strong_consensus():
    stances = [
        {"item_id": "1", "source": "pubmed", "stance": "supports"},
        {"item_id": "2", "source": "chembl", "stance": "supports"},
        {"item_id": "3", "source": "pubchem", "stance": "supports"}
    ]
    res = compute_consensus_meter(stances)
    assert res["label"] == "Strong Consensus"
    assert res["supports"] == 3
    assert res["contradicts"] == 0
    assert res["total_sources"] == 3

def test_mostly_supported():
    stances = [
        {"item_id": "1", "source": "pubmed", "stance": "supports"},
        {"item_id": "2", "source": "chembl", "stance": "mentions"},
        {"item_id": "3", "source": "pubchem", "stance": "mentions"}
    ]
    res = compute_consensus_meter(stances)
    assert res["label"] == "Mostly Supported"
    assert res["supports"] == 1
    assert res["mentions"] == 2

def test_mixed_evidence():
    stances = [
        {"item_id": "1", "source": "pubmed", "stance": "supports"},
        {"item_id": "2", "source": "chembl", "stance": "contradicts"},
        {"item_id": "3", "source": "pubchem", "stance": "supports"}
    ]
    res = compute_consensus_meter(stances)
    assert res["label"] == "Mixed Evidence"
    assert res["supports"] == 2
    assert res["contradicts"] == 1

def test_conflicting():
    stances = [
        {"item_id": "1", "source": "pubmed", "stance": "contradicts"},
        {"item_id": "2", "source": "chembl", "stance": "contradicts"}
    ]
    res = compute_consensus_meter(stances)
    assert res["label"] == "Conflicting"
    assert res["supports"] == 0
    assert res["contradicts"] == 2

def test_no_evidence():
    res = compute_consensus_meter([])
    assert res["label"] == "No Evidence"
    assert res["total_sources"] == 0
