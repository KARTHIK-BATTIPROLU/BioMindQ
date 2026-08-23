import logging
import json
from typing import Dict, Any, List, Optional
from app.config import settings
from app.models.schemas import FinalAnswer
from app.llm.groq_client import call_groq_structured

logger = logging.getLogger(__name__)

FIXED_DISCLAIMER = "Research and informational tool only — not intended for diagnosis or treatment."

ANSWER_GENERATOR_SYSTEM_PROMPT = f"""You are the master BioMindQ research assistant with persistent cross-session memory.
Your job is to produce a final response for a user's biomedical question or conversational query.

Strict Formatting Rule:
FORMAT YOUR "ai_summary" IN CLEAN BULLET POINTS. Every major point, recommendation, or past research session MUST be on a separate line starting with a bullet point ("• ").

Strict Rules:
1. If the user asks about previous conversations, past research, earlier findings, or past sessions, YOU MUST USE THE PROVIDED [USER PAST RESEARCH CONTEXT & MEMORY HISTORY] to list each past session on a separate bulleted line starting with "• ". NEVER state that you cannot recall previous interactions.
2. If evidence items are retrieved, populate "retrieved_evidence": [{{"claim": "...", "source": "...", "url": "...", "stance": "SUPPORTS" | "CONTRASTS" | "MENTIONS"}}].
3. "ai_summary": Your high-level scientific synthesis formatted in clear bullet points on separate lines.
4. "confidence_score": Integer 0 to 100.
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
    planner_output: Optional[Dict[str, Any]] = None,
    past_context: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    intent = (planner_output or {}).get("intent", "database_search")

    if not settings.GROQ_API_KEY:
        logger.info("GROQ_API_KEY not configured; using fallback answer generator.")
        return generate_fallback_answer(question, raw_results, verifier_output, planner_output, past_context)

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

    past_context_str = ""
    if past_context:
        formatted_past = []
        for p in past_context:
            formatted_past.append(f"- Query: \"{p.get('query_text')}\" | Summary: {p.get('summary_text')} | Topics: {', '.join(p.get('topics', []))}")
        past_context_str = "\n[USER PAST RESEARCH CONTEXT & MEMORY HISTORY]:\n" + "\n".join(formatted_past) + "\nNote: The user has persistent research memory. Reference their past sessions above directly when asked about previous conversations or research history!"

    user_prompt = f"""User Input: "{question}"
Query Intent: {intent}
{past_context_str}

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
    planner_output: Optional[Dict[str, Any]] = None,
    past_context: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    intent = (planner_output or {}).get("intent", "database_search")

    if intent == "direct_answer":
        if past_context:
            past_summary_lines = []
            for p in past_context[:3]:
                past_summary_lines.append(f"• In session '{p.get('query_text')}': {p.get('summary_text')}")
            summary_text = f"Based on your persistent research memory, here are your previous research sessions and findings:\n\n" + "\n\n".join(past_summary_lines)
        else:
            summary_text = (
                f"To find the best biomedical solution for '{question}', try asking target questions such as:\n\n"
                "• What is metformin's mechanism on AMPK?\n"
                "• Does ibuprofen interact with lisinopril and reduce antihypertensive efficacy?\n"
                "• Summarize GLP-1 receptor agonist findings on cardiovascular outcomes.\n\n"
                "You can also search specific chemical compounds, target proteins, or disease indications."
            )

        return {
            "retrieved_evidence": [],
            "ai_summary": summary_text,
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
