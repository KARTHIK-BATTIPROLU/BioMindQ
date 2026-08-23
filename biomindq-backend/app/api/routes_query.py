import time
import logging
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Request, status
from app.models.schemas import HealthResponse, QueryRequest, QueryResponse, FinalAnswer, VerifierOutput, ConsensusMeter
from app.db.mongo import check_mongo_health, save_query_record
from app.llm.groq_client import check_groq_health
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
async def process_query(request: QueryRequest, http_request: Request):
    question = request.question.strip()
    if not question:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Question parameter cannot be empty."
        )

    start_time = time.time()
    shared_client = getattr(http_request.app.state, "http_client", None)

    try:
        # Step 1: Planner (LLM #1 - Intent Classification & Search Planning)
        planner_output = await plan_query(question)
        intent = planner_output.get("intent", "database_search")

        # Step 2: Retrieval (Concurrent asyncio.gather only if intent == "database_search")
        if intent == "database_search" and planner_output.get("sources"):
            raw_results = await execute_retrieval(planner_output, http_client=shared_client)
        else:
            raw_results = {"pubmed": [], "chembl": [], "pubchem": [], "drugbank": []}

        # Step 3: Verifier (LLM #2)
        if intent == "database_search" and any(len(items) > 0 for items in raw_results.values()):
            verifier_dict = await verify_evidence(question, raw_results)
        else:
            verifier_dict = {
                "entities_linked": [],
                "agreements": ["Direct AI assistant response processed."],
                "conflicts": [],
                "confidence": 100,
                "item_stances": []
            }

        # Step 4: Consensus Meter calculation
        item_stances = verifier_dict.get("item_stances", [])
        if intent == "direct_answer" or not item_stances:
            consensus_dict = {
                "label": "Direct Response",
                "supports": 0,
                "contradicts": 0,
                "mentions": 0,
                "total_sources": 0
            }
        else:
            consensus_dict = compute_consensus_meter(item_stances)

        # Step 5: Answer Generator (LLM #3)
        final_answer_dict = await generate_final_answer(question, raw_results, verifier_dict, planner_output)

        latency_ms = (time.time() - start_time) * 1000.0

        # Build response models
        final_answer = FinalAnswer.model_validate(final_answer_dict)
        verifier_output = VerifierOutput.model_validate(verifier_dict)
        consensus = ConsensusMeter.model_validate(consensus_dict)

        # Step 6: Persist full query record to MongoDB queries collection
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

    except Exception as e:
        logger.error(f"Error processing query '{question}': {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while processing your research query: {str(e)}"
        )
