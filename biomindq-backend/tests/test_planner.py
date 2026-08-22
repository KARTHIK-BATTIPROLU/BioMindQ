import pytest
from app.pipeline.planner import plan_query

SAMPLE_QUESTIONS = [
    ("compound_lookup", "What is known about metformin's interaction with AMPK?"),
    ("disease_overview", "What compounds are being studied for early-stage Alzheimer's?"),
    ("interaction_check", "Does ibuprofen interact with lisinopril?"),
    ("literature_scan", "Summarize recent findings on GLP-1 receptor agonists."),
    ("out_of_scope", "What is the capital of France and what is the weather like?")
]

@pytest.mark.asyncio
@pytest.mark.parametrize("category,question", SAMPLE_QUESTIONS)
async def test_planner_questions(category, question):
    plan = await plan_query(question)
    assert isinstance(plan, dict)
    assert "sources" in plan
    assert "per_source_query" in plan
    assert isinstance(plan["sources"], list)
    assert isinstance(plan["per_source_query"], dict)

    if category == "out_of_scope":
        print(f"\n[Planner - Out of Scope] Question: '{question}' => Sources: {plan['sources']}")
    else:
        assert len(plan["sources"]) > 0, f"Planner should select sources for {category}"
        print(f"\n[Planner - {category}] Sources: {plan['sources']} | Queries: {plan['per_source_query']}")
