import logging
import json
from typing import Optional, Dict, Any, Type, List
from pydantic import BaseModel
from groq import AsyncGroq
from app.config import settings

logger = logging.getLogger(__name__)

class GroqClientManager:
    client: Optional[AsyncGroq] = None

groq_manager = GroqClientManager()

def init_groq_client():
    if settings.GROQ_API_KEY:
        groq_manager.client = AsyncGroq(api_key=settings.GROQ_API_KEY, max_retries=0)
    else:
        groq_manager.client = None

async def check_groq_health() -> str:
    if not settings.GROQ_API_KEY:
        return "missing_api_key"
    try:
        if not groq_manager.client:
            init_groq_client()
        if groq_manager.client:
            await groq_manager.client.models.list()
            return "ok"
        return "unreachable"
    except Exception as e:
        logger.warning(f"Groq API health check failed: {e}")
        return "unreachable"

async def call_groq_structured(
    model: str,
    system_prompt: str,
    user_prompt: str,
    response_schema: Type[BaseModel],
    temperature: float = 0.1
) -> Dict[str, Any]:
    if not groq_manager.client:
        init_groq_client()
    
    if not groq_manager.client:
        raise ValueError("GROQ_API_KEY is not configured in environment.")

    formatted_system_prompt = system_prompt
    if "json" not in formatted_system_prompt.lower():
        formatted_system_prompt += "\nRespond strictly in valid JSON format."

    candidate_models: List[str] = [
        "llama3-70b-8192",
        "llama3-8b-8192",
        "mixtral-8x7b-32768",
        "gemma2-9b-it",
        "groq/compound-mini"
    ]

    candidate_models = list(dict.fromkeys(candidate_models))
    last_exception = None

    for m in candidate_models:
        try:
            response = await groq_manager.client.chat.completions.create(
                model=m,
                messages=[
                    {"role": "system", "content": formatted_system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                response_format={"type": "json_object"},
                temperature=temperature
            )

            content = response.choices[0].message.content
            data = json.loads(content)
            validated = response_schema.model_validate(data)
            logger.info(f"Groq structured LLM call succeeded using model '{m}'.")
            return validated.model_dump()

        except Exception as e:
            last_exception = e
            logger.warning(f"Groq call with model '{m}' encountered error: {e}. Trying next candidate model...")

    raise RuntimeError(f"All candidate Groq models failed. Last error: {last_exception}")
