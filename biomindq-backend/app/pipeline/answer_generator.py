import logging
import json
from typing import Dict, Any, List
from app.config import settings
from app.models.schemas import FinalAnswer
from app.llm.groq_client import call_groq_structured

logger = logging.getLogger(__name__)

FIXED_DISCLAIMER = "Research and informational tool only — not intended for diagnosis or treatment."

ANSWER_GENERATOR_SYSTEM_PROMPT = f"""You are the master BioMindQ answer generator.
Your job is to produce a final response for a user's biomedical question, strictly separating RETRIEVED EVIDENCE from AI SUMMARY.

Strict Rules:
1. "retrieved_evidence": Array of objects `{{"claim": "...", "source": "...", "url": "...", "stance": "SUPPORTS" | "CONTRASTS" | "MENTIONS"}}`. Every claim MUST be directly traceable to one of the provided database search results. Include exact URLs and assign stance:
   - "SUPPORTS": directly confirms/supports the claim.
   - "CONTRASTS": contradicts, attenuates, or highlights adverse interaction/warning.
   - "MENTIONS": topically relevant but does not directly confirm or contradict.
2. "ai_summary": Your high-level synthesis explaining the answer in clear scientific language.
3. "confidence_score": Integer 0 to 100 based on verifier evaluation.
4. "disclaimer": Must always be exactly "{FIXED_DISCLAIMER}".

Respond strictly in valid JSON format matching:
{{
  "retrieved_evidence": [{{"claim": "string", "source": "string", "url": "string", "stance": "SUPPORTS" | "CONTRASTS" | "MENTIONS"}}],
  "ai_summary": "string",
  "confidence_score": int,
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

    compact_data = {}
    for src, items in raw_results.items():
        compact_data[src] = [
            {
                "id": item.get("id"),
                "title": item.get("title"),
                "summary": str(item.get("summary", ""))[:150],
                "url": item.get("url")
            }
            for item in items[:3]
        ]

    user_prompt = f"""Question: "{question}"

Verifier Evaluation & Stance Tags:
{json.dumps(verifier_output, indent=2)}

Retrieved Evidence Items:
{json.dumps(compact_data, indent=2)}
"""

    try:
        answer_dict = await call_groq_structured(
            model="openai/gpt-oss-120b",
            system_prompt=ANSWER_GENERATOR_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            response_schema=FinalAnswer,
            temperature=0.2
        )
        answer_dict["disclaimer"] = FIXED_DISCLAIMER
        
        # Ensure each retrieved evidence item has a valid stance tag
        for item in answer_dict.get("retrieved_evidence", []):
            if not item.get("stance") or item["stance"] not in ["SUPPORTS", "CONTRASTS", "MENTIONS"]:
                item["stance"] = "SUPPORTS"

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
    item_stances = verifier_output.get("item_stances", [])
    stance_map = {st.get("item_id"): st.get("stance", "").upper() for st in item_stances}

    for src, items in raw_results.items():
        for idx, item in enumerate(items[:3]):
            item_id = str(item.get("id", f"{src}_{idx}"))
            raw_st = stance_map.get(item_id, "SUPPORTS")
            if raw_st in ["CONTRADICTS", "CONTRASTS"]:
                st_tag = "CONTRASTS"
            elif raw_st in ["MENTIONS", "MIXED"]:
                st_tag = "MENTIONS"
            else:
                st_tag = "SUPPORTS"

            claim_text = f"{item.get('title', '')}: {item.get('summary', '')}"
            retrieved_evidence.append({
                "claim": claim_text[:200],
                "source": src,
                "url": item.get("url", ""),
                "stance": st_tag
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
