import pytest
from app.pipeline.answer_generator import generate_final_answer, FIXED_DISCLAIMER

@pytest.mark.asyncio
async def test_answer_generator_output_structure():
    question = "What is known about metformin's interaction with AMPK?"
    raw_results = {
        "pubmed": [{"id": "1", "title": "Metformin & AMPK", "summary": "Activates AMPK via complex I inhibition.", "url": "https://pubmed.ncbi.nlm.nih.gov/1/", "source": "pubmed"}],
        "chembl": [{"id": "CHEMBL1431", "title": "Metformin", "summary": "IC50 = 12.4 uM", "url": "https://www.ebi.ac.uk/chembl/compound_report_card/CHEMBL1431/", "source": "chembl"}],
        "pubchem": [],
        "drugbank": []
    }
    verifier_output = {
        "entities_linked": [{"entity": "Metformin", "sources": ["pubmed", "chembl"]}],
        "agreements": ["Independent agreement confirmed."],
        "conflicts": [],
        "confidence": 94
    }

    final_answer = await generate_final_answer(question, raw_results, verifier_output)
    
    assert isinstance(final_answer, dict)
    assert "retrieved_evidence" in final_answer
    assert "ai_summary" in final_answer
    assert "confidence_score" in final_answer
    assert "disclaimer" in final_answer

    assert isinstance(final_answer["retrieved_evidence"], list)
    assert len(final_answer["retrieved_evidence"]) > 0
    assert isinstance(final_answer["ai_summary"], str)
    assert len(final_answer["ai_summary"]) > 0
    assert isinstance(final_answer["confidence_score"], int)
    assert final_answer["disclaimer"] == FIXED_DISCLAIMER

    print(f"\n[Answer Generator Test]")
    print(f"Evidence Count: {len(final_answer['retrieved_evidence'])}")
    print(f"AI Summary: {final_answer['ai_summary']}")
    print(f"Confidence Score: {final_answer['confidence_score']}%")
    print(f"Disclaimer: {final_answer['disclaimer']}")
