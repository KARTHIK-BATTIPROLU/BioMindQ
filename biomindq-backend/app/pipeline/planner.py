import logging
from typing import Dict, Any, List
from app.config import settings
from app.models.schemas import PlannerOutput
from app.llm.groq_client import call_groq_structured

logger = logging.getLogger(__name__)

PLANNER_SYSTEM_PROMPT = """You are an expert biomedical research planner.
Your job is to analyze a user's research question and select which biomedical database sources are genuinely relevant, then format specific search queries for each selected source.

Available sources:
1. "pubmed": Best for scientific literature, clinical trials, disease overviews, mechanisms, and recent research findings. (Format query as key research terms/keywords).
2. "chembl": Best for chemical compounds, bioactivity assay data, target binding affinities, IC50/Ki values. (Format query as compound/drug name or target).
3. "pubchem": Best for chemical structures, compound descriptions, molecular properties, and CAS numbers. (Format query as compound/drug name).
4. "drugbank": Best for drug mechanisms of action, drug-drug interactions, dosages, and pharmacology. (Format query as drug name).

Rules:
- Only include sources in "sources" that are relevant to the question.
- Always provide "per_source_query" entries for selected sources.
- If the question is completely out-of-scope or non-biomedical, return empty sources list [].

Respond strictly in valid JSON format matching:
{
  "sources": ["string"],
  "per_source_query": {"source_name": "query_string"}
}
"""

async def plan_query(question: str) -> Dict[str, Any]:
    if not settings.GROQ_API_KEY:
        logger.info("GROQ_API_KEY not configured; using rule-based fallback planner.")
        return generate_fallback_plan(question)

    user_prompt = f"Analyze this biomedical question and plan data retrieval:\n\"{question}\""

    try:
        plan_dict = await call_groq_structured(
            model="groq/compound-mini",
            system_prompt=PLANNER_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            response_schema=PlannerOutput,
            temperature=0.1
        )
        return plan_dict
    except Exception as e:
        logger.error(f"Planner LLM call failed: {e}. Falling back to rule-based planner.")
        return generate_fallback_plan(question)

def generate_fallback_plan(question: str) -> Dict[str, Any]:
    q_lower = question.lower()
    sources: List[str] = []
    per_source_query: Dict[str, str] = {}

    words = [w.strip("?,.!") for w in q_lower.split()]
    main_terms = [w for w in words if len(w) > 3 and w not in ["what", "does", "with", "from", "about", "have", "this", "that", "how"]]
    query_str = " ".join(main_terms[:3]) if main_terms else question

    if any(k in q_lower for k in ["interact", "interaction", "drug", "ibuprofen", "lisinopril", "metformin"]):
        sources.extend(["pubmed", "chembl", "pubchem", "drugbank"])
    elif any(k in q_lower for k in ["alzheimer", "cancer", "disease", "clinical", "trial", "study", "agonist"]):
        sources.extend(["pubmed", "chembl"])
    elif any(k in q_lower for k in ["compound", "structure", "smiles", "chembl", "pubchem"]):
        sources.extend(["chembl", "pubchem"])
    elif len(main_terms) > 0 and not any(k in q_lower for k in ["capital", "weather", "recipe", "sport", "movie"]):
        sources.extend(["pubmed", "chembl", "pubchem"])

    for s in sources:
        per_source_query[s] = query_str

    return {
        "sources": list(dict.fromkeys(sources)),
        "per_source_query": per_source_query
    }
