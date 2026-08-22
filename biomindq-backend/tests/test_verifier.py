import pytest
from app.pipeline.verifier import verify_evidence

@pytest.mark.asyncio
async def test_verifier_agreement_scenario():
    question = "What is known about metformin's interaction with AMPK?"
    raw_results = {
        "pubmed": [{"id": "1", "title": "Metformin activates AMPK", "summary": "Study proves metformin activates AMPK via complex I.", "url": "https://pubmed.ncbi.nlm.nih.gov/1/", "source": "pubmed"}],
        "chembl": [{"id": "CHEMBL1431", "title": "Metformin", "summary": "Target: AMPK activator IC50=12.4uM", "url": "https://www.ebi.ac.uk/chembl/compound_report_card/CHEMBL1431/", "source": "chembl"}],
        "pubchem": [],
        "drugbank": []
    }
    
    verifier_output = await verify_evidence(question, raw_results)
    assert isinstance(verifier_output, dict)
    assert "confidence" in verifier_output
    assert "agreements" in verifier_output
    assert verifier_output["confidence"] >= 65
    assert len(verifier_output["agreements"]) > 0
    print(f"\n[Verifier Agreement Test] Confidence: {verifier_output['confidence']}% | Agreements: {verifier_output['agreements']}")

@pytest.mark.asyncio
async def test_verifier_conflict_scenario():
    question = "Does ibuprofen interact with lisinopril?"
    raw_results = {
        "pubmed": [{"id": "2", "title": "NSAID ACE Inhibitor Interaction", "summary": "Ibuprofen attenuates antihypertensive effect of Lisinopril.", "url": "https://pubmed.ncbi.nlm.nih.gov/2/", "source": "pubmed"}],
        "chembl": [],
        "pubchem": [],
        "drugbank": []
    }

    verifier_output = await verify_evidence(question, raw_results)
    assert isinstance(verifier_output, dict)
    assert "conflicts" in verifier_output
    assert len(verifier_output["conflicts"]) > 0
    print(f"\n[Verifier Conflict Test] Conflicts surfaced: {verifier_output['conflicts']}")
