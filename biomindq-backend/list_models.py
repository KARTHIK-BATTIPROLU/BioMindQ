import asyncio
from groq import AsyncGroq
from app.config import settings

async def main():
    client = AsyncGroq(api_key=settings.GROQ_API_KEY)
    models = await client.models.list()
    print("Available Groq models:")
    for m in models.data:
        print(" -", m.id)

if __name__ == "__main__":
    asyncio.run(main())
