import logging
import json
from typing import Dict, Any, List, Optional
from app.config import settings
from app.models.schemas import FinalAnswer
from app.llm.groq_client import call_groq_structured

logger = logging.getLogger(__name__)

FIXED_DISCLAIMER = "Research and informational tool only — not intended for diagnosis or treatment."

ANSWER_GENERATOR_SYSTEM_PROMPT = f"""You are the master BioMindQ answer generator.
Your job is to produce a final response for a user's biomedical question or conversational query.

Strict Rules:
1. If the user's input is a conversational follow-up, advice request, or meta question, provide a clear, helpful direct scientific synthesis in "ai_summary" and set "retrieved_evidence": [].
2. If evidence items are provided, populate "retrieved_evidence": [{{"claim": "...", "source": "...", "url": "...", "stance": "SUPPORTS" | "CONTRASTS" | "MENTIONS"}}].
3. "ai_summary": Your high-level synthesis explaining the answer in clear scientific language.
4. "confidence_score": Integer 0 to 100 based on evaluation.
5. "disclaimer": Must always be exactly "{FIXED_DISCLAIMER}".

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
    verifier_output: Dict[str, Any],
    planner_output: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    intent = (planner_output or {}).get("intent", "database_search")

    if not settings.GROQ_API_KEY:
        logger.info("GROQ_API_KEY not configured; using fallback answer generator.")
        return generate_fallback_answer(question, raw_results, verifier_output, planner_output)

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

    user_prompt = f"""User Input: "{question}"
Query Intent: {intent}

Verifier Evaluation:
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

        if intent == "direct_answer":
            answer_dict["retrieved_evidence"] = []
            answer_dict["confidence_score"] = 100
        else:
            for item in answer_dict.get("retrieved_evidence", []):
                if not item.get("stance") or item["stance"] not in ["SUPPORTS", "CONTRASTS", "MENTIONS"]:
                    item["stance"] = "SUPPORTS"

        return answer_dict
    except Exception as e:
        logger.error(f"Answer Generator LLM call failed: {e}. Using fallback answer generator.")
        return generate_fallback_answer(question, raw_results, verifier_output, planner_output)

def generate_fallback_answer(
    question: str,
    raw_results: Dict[str, List[Dict[str, Any]]],
    verifier_output: Dict[str, Any],
    planner_output: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    intent = (planner_output or {}).get("intent", "database_search")

    if intent == "direct_answer":
        return {
            "retrieved_evidence": [],
            "ai_summary": f"To find the best biomedical solution for '{question}', try asking a specific target question such as: 1) 'What is metformin's mechanism on AMPK?', 2) 'Does ibuprofen interact with lisinopril?', or 3) 'Summarize GLP-1 receptor agonist findings'. You can also search specific chemical compounds, target proteins, or disease indications.",
            "confidence_score": 100,
            "disclaimer": FIXED_DISCLAIMER
        }

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
