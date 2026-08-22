import logging
from typing import Dict, Any, List
from app.config import settings
from app.models.schemas import FinalAnswer
from app.llm.groq_client import call_groq_structured

logger = logging.getLogger(__name__)

FIXED_DISCLAIMER = "Research and informational tool only — not intended for diagnosis or treatment."

ANSWER_GENERATOR_SYSTEM_PROMPT = f"""You are the master BioMindQ answer generator.
Your job is to produce a final response for a user's biomedical question, strictly separating RETRIEVED EVIDENCE from AI SUMMARY.

Strict Rules:
1. "retrieved_evidence": Must be an array of objects `{{"claim": "...", "source": "...", "url": "..."}}`. Every claim MUST be directly traceable to one of the provided database search results. Include exact URLs provided in source items.
2. "ai_summary": Your high-level synthesis explaining the answer in clear scientific language. Do NOT blend unsourced claims into retrieved_evidence.
3. "confidence_score": Integer 0 to 100 based on verifier evaluation.
4. "disclaimer": Must always be exactly "{FIXED_DISCLAIMER}".

Return JSON schema matching:
{{
  "retrieved_evidence": [{{"claim": "string", "source": "string", "url": "string"}}],
  "ai_summary": "string",
  "confidence_score": int (0-100),
  "disclaimer": "{FIXED_DISCLAIMER}"
}}
"""

async def generate_final_answer(
    question: str,
    raw_results: Dict[str, List[Dict[str, Any]]],
    verifier_output: Dict[str, Any]
) -> Dict[str, Any]:
    if not settings.GROQ_API_KEY:
        logger.info("GROQ_API_KEY not configured; using fallback answer generator.")
        return generate_fallback_answer(question, raw_results, verifier_output)

    user_prompt = f"""Question: "{question}"

Verifier Evaluation:
{verifier_output}

Raw Retrieved Evidence Items by Source:
{raw_results}
"""

    try:
        answer_dict = await call_groq_structured(
            model="llama-3.3-70b-versatile",
            system_prompt=ANSWER_GENERATOR_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            response_schema=FinalAnswer,
            temperature=0.2
        )
        # Ensure fixed disclaimer is strictly set
        answer_dict["disclaimer"] = FIXED_DISCLAIMER
        return answer_dict
    except Exception as e:
        logger.error(f"Answer Generator LLM call failed: {e}. Using fallback answer generator.")
        return generate_fallback_answer(question, raw_results, verifier_output)

def generate_fallback_answer(
    question: str,
    raw_results: Dict[str, List[Dict[str, Any]]],
    verifier_output: Dict[str, Any]
) -> Dict[str, Any]:
    retrieved_evidence = []

    for src, items in raw_results.items():
        for item in items[:3]:
            claim_text = f"{item.get('title', '')}: {item.get('summary', '')}"
            retrieved_evidence.append({
                "claim": claim_text[:200],
                "source": src,
                "url": item.get("url", "")
            })

    confidence = verifier_output.get("confidence", 50)
    agreements = verifier_output.get("agreements", [])
    conflicts = verifier_output.get("conflicts", [])

    summary_parts = [f"Synthesis for query: '{question}'."]
    if agreements:
        summary_parts.append(f"Agreements noted: {'; '.join(agreements)}")
    if conflicts:
        summary_parts.append(f"Warnings/Conflicts: {'; '.join(conflicts)}")
    if not retrieved_evidence:
        summary_parts.append("No active external database records were found for this query.")

    ai_summary = " ".join(summary_parts)

    return {
        "retrieved_evidence": retrieved_evidence,
        "ai_summary": ai_summary,
        "confidence_score": confidence,
        "disclaimer": FIXED_DISCLAIMER
    }
