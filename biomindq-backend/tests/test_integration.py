import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.config import settings

client = TestClient(app)

SAMPLE_INTEGRATION_QUESTIONS = [
    "What is known about metformin's interaction with AMPK?",
    "What compounds are being studied for early-stage Alzheimer's?",
    "Does ibuprofen interact with lisinopril?",
    "Summarize recent findings on GLP-1 receptor agonists.",
    "What is the capital of France?"
]

def test_cors_headers():
    response = client.options("/api/query", headers={"Origin": "https://bio-mind-q.vercel.app", "Access-Control-Request-Method": "POST"})
    assert response.status_code in [200, 204]
    assert response.headers.get("access-control-allow-origin") in ["*", "https://bio-mind-q.vercel.app"]

@pytest.mark.parametrize("question", SAMPLE_INTEGRATION_QUESTIONS)
def test_end_to_end_query_pipeline(question):
    response = client.post("/api/query", json={"question": question})
    assert response.status_code == 200
    data = response.json()

    assert "final_answer" in data
    assert "verifier_output" in data
    assert "latency_ms" in data

    final = data["final_answer"]
    assert "retrieved_evidence" in final
    assert "ai_summary" in final
    assert "confidence_score" in final
    assert "disclaimer" in final
    assert final["disclaimer"] == "Research and informational tool only — not intended for diagnosis or treatment."

    print(f"\n[E2E Integration Passed] Question: '{question}' | Latency: {data['latency_ms']}ms | Evidence Items: {len(final['retrieved_evidence'])}")

def test_drugbank_gated_behavior(monkeypatch):
    # Case 1: Without DRUGBANK_API_KEY
    monkeypatch.setattr(settings, "DRUGBANK_API_KEY", "")
    resp1 = client.post("/api/query", json={"question": "Does metformin interact with AMPK?"})
    assert resp1.status_code == 200

    # Case 2: With dummy DRUGBANK_API_KEY
    monkeypatch.setattr(settings, "DRUGBANK_API_KEY", "dummy_key_123")
    resp2 = client.post("/api/query", json={"question": "Does metformin interact with AMPK?"})
    assert resp2.status_code == 200
    print("\n[DrugBank Gate Test Passed] Successfully toggled DRUGBANK_API_KEY without code modifications.")
