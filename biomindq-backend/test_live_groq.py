import asyncio
import json
from app.pipeline.planner import plan_query
from app.pipeline.retrieval import execute_retrieval
from app.pipeline.verifier import verify_evidence
from app.pipeline.answer_generator import generate_final_answer

async def run_live_test():
    question = "What is known about metformin's interaction with AMPK?"
    print(f"\n--- 1. PLANNER (Groq LLM) ---")
    plan = await plan_query(question)
    print(json.dumps(plan, indent=2))

    print(f"\n--- 2. RETRIEVAL (PubMed + ChEMBL + PubChem) ---")
    raw_results = await execute_retrieval(plan)
    for src, items in raw_results.items():
        print(f"Source '{src}': {len(items)} items retrieved")

    print(f"\n--- 3. VERIFIER (Groq LLM) ---")
    verifier = await verify_evidence(question, raw_results)
    print(json.dumps(verifier, indent=2))

    print(f"\n--- 4. ANSWER GENERATOR (Groq LLM) ---")
    answer = await generate_final_answer(question, raw_results, verifier)
    print(json.dumps(answer, indent=2))

if __name__ == "__main__":
    asyncio.run(run_live_test())
