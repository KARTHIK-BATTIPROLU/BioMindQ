import pytest
import asyncio
from app.memory.vector_store import compute_embedding, cosine_similarity, retrieve_past_context_with_timeout

def test_embedding_computation():
    text1 = "Metformin activates AMPK and improves insulin sensitivity."
    text2 = "AMPK activation by metformin suppresses gluconeogenesis."
    text3 = "Quantum computing and astronomy telescopes."

    v1 = compute_embedding(text1)
    v2 = compute_embedding(text2)
    v3 = compute_embedding(text3)

    assert len(v1) > 0
    sim_12 = cosine_similarity(v1, v2)
    sim_13 = cosine_similarity(v1, v3)

    assert sim_12 > sim_13

@pytest.mark.asyncio
async def test_vector_recall_timeout_fallback():
    # Test that context recall returns within 1.5s timeout budget or falls back cleanly
    start = asyncio.get_event_loop().time()
    res = await retrieve_past_context_with_timeout(
        user_id="test_user_nonexistent",
        question="What is known about metformin?",
        extracted_topics=["metformin"],
        timeout_seconds=0.1
    )
    duration = asyncio.get_event_loop().time() - start
    assert duration < 1.0
    assert isinstance(res, list)
