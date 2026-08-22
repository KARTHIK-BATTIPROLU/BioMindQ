import logging
import json
from typing import Optional, Dict, Any, Type
from pydantic import BaseModel
import httpx
from groq import AsyncGroq
from app.config import settings

logger = logging.getLogger(__name__)

class GroqClientManager:
    client: Optional[AsyncGroq] = None

groq_manager = GroqClientManager()

def init_groq_client():
    if settings.GROQ_API_KEY:
        groq_manager.client = AsyncGroq(api_key=settings.GROQ_API_KEY)
    else:
        groq_manager.client = None

async def check_groq_health() -> str:
    if not settings.GROQ_API_KEY:
        return "missing_api_key"
    try:
        if not groq_manager.client:
            init_groq_client()
        # Test call with tiny completion or models list
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

    json_schema = response_schema.model_json_schema()

    response = await groq_manager.client.chat.completions.create(
        model=model,
        messages=[
          {"role": "system", "content": system_prompt},
          {"role": "user", "content": user_prompt}
        ],
        response_format={
          "type": "json_object"
        },
        temperature=temperature
    )

    content = response.choices[0].message.content
    try:
        data = json.loads(content)
        # Validate against schema
        validated = response_schema.model_validate(data)
        return validated.model_dump()
    except Exception as e:
        logger.error(f"Failed to parse structured LLM output: {e}. Raw content: {content}")
        raise RuntimeError(f"Structured output validation failed: {e}")
