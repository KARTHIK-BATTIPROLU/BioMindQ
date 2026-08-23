import logging
from typing import Dict, Any, List
from app.config import settings
from app.models.schemas import PlannerOutput
from app.llm.groq_client import call_groq_structured

logger = logging.getLogger(__name__)

PLANNER_SYSTEM_PROMPT = """You are an expert biomedical research planner and query intent classifier.
Your job is to analyze a user's input and determine whether it requires querying external biomedical databases or should be answered directly as a conversational response.

Classify into one of two intents:
1. "direct_answer": For conversational follow-ups, general advice, meta-questions, greetings, or questions that do NOT ask for specific molecular, pharmacological, or clinical literature data (e.g., "how can I find a better solution?", "explain this further", "hello", "what databases do you use?").
   - Set "sources": []
   - Set "per_source_query": {}

2. "database_search": For questions requesting specific biomedical research data, chemical structures, bioactivity assays, drug interactions, clinical trials, or mechanisms.
   - Select relevant sources from: "pubmed", "chembl", "pubchem", "drugbank".
   - Format specific search queries per selected source in "per_source_query".

Available sources for "database_search":
- "pubmed": Scientific literature, clinical trials, disease mechanisms.
- "chembl": Bioactivity assays, target binding affinities, IC50/Ki values.
- "pubchem": Chemical structures, molecular properties, CAS numbers.
- "drugbank": Drug mechanisms of action, drug-drug interactions, pharmacology.

Respond strictly in valid JSON format matching:
{
  "intent": "database_search" | "direct_answer",
  "reasoning": "string",
  "sources": ["string"],
  "per_source_query": {"source_name": "query_string"}
}
"""

async def plan_query(question: str) -> Dict[str, Any]:
    if not settings.GROQ_API_KEY:
        logger.info("GROQ_API_KEY not configured; using rule-based fallback planner.")
        return generate_fallback_plan(question)

    user_prompt = f"Analyze this user input and determine query intent & plan:\n\"{question}\""

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
    q_lower = question.lower().strip()
    
    conversational_triggers = [
        "how can i", "how to", "best solution", "better solution", "what is this",
        "explain", "help me", "hello", "hi", "thanks", "who are you", "what can you do",
        "show me", "tell me", "what next", "solution", "guide me"
    ]
    
    biomedical_keywords = [
        "metformin", "ampk", "ibuprofen", "lisinopril", "glp-1", "alzheimer", "cancer",
        "inhibitor", "agonist", "antagonist", "kinase", "receptor", "assay", "smiles",
        "ic50", "drug", "trial", "compound", "gene", "protein", "dna", "rna", "disease",
        "interaction", "side effect", "pharmacology", "chembl", "pubmed", "pubchem", "drugbank"
    ]

    has_conversational = any(t in q_lower for t in conversational_triggers)
    has_biomedical = any(b in q_lower for b in biomedical_keywords)

    if has_conversational and not has_biomedical:
        return {
            "intent": "direct_answer",
            "reasoning": "Conversational / follow-up query detected without specific biomedical entity target.",
            "sources": [],
            "per_source_query": {}
        }

    sources: List[str] = []
    per_source_query: Dict[str, str] = {}

    words = [w.strip("?,.!") for w in q_lower.split()]
    main_terms = [w for w in words if len(w) > 3 and w not in ["what", "does", "with", "from", "about", "have", "this", "that", "how", "find", "solution"]]
    query_str = " ".join(main_terms[:3]) if main_terms else question

    if any(k in q_lower for k in ["interact", "interaction", "drug", "ibuprofen", "lisinopril", "metformin"]):
        sources.extend(["pubmed", "chembl", "pubchem", "drugbank"])
    elif any(k in q_lower for k in ["alzheimer", "cancer", "disease", "clinical", "trial", "study", "agonist"]):
        sources.extend(["pubmed", "chembl"])
    elif any(k in q_lower for k in ["compound", "structure", "smiles", "chembl", "pubchem"]):
        sources.extend(["chembl", "pubchem"])
    elif has_biomedical:
        sources.extend(["pubmed", "chembl", "pubchem"])
    else:
        return {
            "intent": "direct_answer",
            "reasoning": "General non-target input.",
            "sources": [],
            "per_source_query": {}
        }

    for s in sources:
        per_source_query[s] = query_str

    return {
        "intent": "database_search",
        "reasoning": "Biomedical research query requiring external database search.",
        "sources": list(dict.fromkeys(sources)),
        "per_source_query": per_source_query
    }
