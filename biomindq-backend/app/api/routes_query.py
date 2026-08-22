import time
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException, Request, Response, Depends, status
from app.models.schemas import HealthResponse, QueryRequest, QueryResponse, FinalAnswer, VerifierOutput, ConsensusMeter
from app.db.mongo import check_mongo_health, save_query_record, mongo_manager
from app.llm.groq_client import check_groq_health
from app.auth.dependencies import verify_trial_or_auth, record_trial_usage
from app.memory.vector_store import retrieve_past_context_with_timeout, embed_and_upsert_session
from app.memory.graph import upsert_session_graph
from app.pipeline.planner import plan_query
from app.pipeline.retrieval import execute_retrieval
from app.pipeline.verifier import verify_evidence
from app.pipeline.answer_generator import generate_final_answer
from app.pipeline.consensus import compute_consensus_meter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["query"])

@router.get("/health", response_model=HealthResponse)
async def health_check():
    mongo_status = await check_mongo_health()
    groq_status = await check_groq_health()
    return HealthResponse(mongo=mongo_status, groq=groq_status)

@router.post("/query", response_model=QueryResponse)
async def process_query(
    request: QueryRequest,
    http_request: Request,
    response: Response,
    auth_ctx: Dict[str, Any] = Depends(verify_trial_or_auth)
):
    question = request.question.strip()
    if not question:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Question parameter cannot be empty."
        )

    start_time = time.time()
    shared_client = getattr(http_request.app.state, "http_client", None)
    user = auth_ctx.get("user")
    is_authenticated = auth_ctx.get("is_authenticated", False)
    user_id = user["id"] if user else None

    try:
        # Step 0: Context Recall (Phase 4 - Graph-Guided Vector Recall with 1.5s timeout budget)
        past_context_str = ""
        extracted_topics_pre = [w.strip() for w in question.split() if len(w) > 4]
        if is_authenticated and user_id:
            try:
                past_sessions = await retrieve_past_context_with_timeout(
                    user_id=user_id,
                    question=question,
                    extracted_topics=extracted_topics_pre,
                    timeout_seconds=1.5
                )
                if past_sessions:
                    context_snippets = [
                        f"Previous Session Query: '{s['query_text']}' -> Summary: {s['summary_text']}"
                        for s in past_sessions
                    ]
                    past_context_str = "\n".join(context_snippets)
                    logger.info(f"Retrieved {len(past_sessions)} past context sessions for user {user_id}.")
            except Exception as e:
                logger.warning(f"Error executing past context recall: {e}")

        # Step 1: Planner (LLM #1) with past context injection if available
        planner_question = question
        if past_context_str:
            planner_question = f"{question}\n\n[USER PAST RESEARCH CONTEXT]:\n{past_context_str}"

        planner_output = await plan_query(planner_question)

        # Step 2: Retrieval (Concurrent asyncio.gather)
        raw_results = await execute_retrieval(planner_output, http_client=shared_client)

        # Step 3: Verifier (LLM #2 - Entity linking & stance tagging)
        verifier_dict = await verify_evidence(question, raw_results)

        # Step 4: Deterministic Consensus Meter calculation
        item_stances = verifier_dict.get("item_stances", [])
        consensus_dict = compute_consensus_meter(item_stances)

        # Step 5: Answer Generator (LLM #3)
        final_answer_dict = await generate_final_answer(question, raw_results, verifier_dict)

        latency_ms = (time.time() - start_time) * 1000.0

        # Build response models
        final_answer = FinalAnswer.model_validate(final_answer_dict)
        verifier_output = VerifierOutput.model_validate(verifier_dict)
        consensus = ConsensusMeter.model_validate(consensus_dict)

        # Extract topics from compounds & entities
        topics = list(set([
            e.lower().strip() for e in verifier_dict.get("entities", []) if e.strip()
        ] + [
            c.get("name", "").lower().strip() for c in verifier_dict.get("compounds", []) if c.get("name")
        ]))
        if not topics:
            topics = [w.lower().strip() for w in question.split() if len(w) > 4][:5]

        answer_payload = {
            "final_answer": final_answer_dict,
            "verifier_output": verifier_dict,
            "consensus": consensus_dict,
            "latency_ms": round(latency_ms, 2)
        }

        # Step 6: Save Record
        if is_authenticated and user_id and mongo_manager.db is not None:
            # Phase 2: Save Session tied to User Identity
            session_doc = {
                "user_id": user_id,
                "created_at": datetime.now(timezone.utc),
                "query_text": question,
                "answer_payload": answer_payload,
                "topics": topics
            }
            res = await mongo_manager.db["sessions"].insert_one(session_doc)
            session_id = str(res.inserted_id)

            # Phase 3: Knowledge Graph MERGE-style Upsert
            try:
                await upsert_session_graph(
                    user_id=user_id,
                    session_id=session_id,
                    query_text=question,
                    topics=topics
                )
            except Exception as e:
                logger.error(f"Error updating knowledge graph: {e}")

            # Phase 4: Embed & Upsert to Vector Store
            summary_text = final_answer_dict.get("ai_summary", "")
            try:
                await embed_and_upsert_session(
                    user_id=user_id,
                    session_id=session_id,
                    query_text=question,
                    summary_text=summary_text,
                    topics=topics
                )
            except Exception as e:
                logger.error(f"Error updating vector store: {e}")

        else:
            # Record Anonymous Trial Usage
            trial_token = auth_ctx.get("trial_token")
            if trial_token:
                await record_trial_usage(trial_token)

            # Log to generic query records
            query_record = {
                "question": question,
                "created_at": datetime.now(timezone.utc),
                "planner_output": planner_output,
                "raw_results": raw_results,
                "verifier_output": verifier_dict,
                "consensus": consensus_dict,
                "final_answer": final_answer_dict,
                "latency_ms": round(latency_ms, 2)
            }
            await save_query_record(query_record)

        return QueryResponse(
            final_answer=final_answer,
            verifier_output=verifier_output,
            consensus=consensus,
            latency_ms=round(latency_ms, 2)
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing query '{question}': {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while processing your research query: {str(e)}"
        )
