import os
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    MONGODB_URI: str = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
    MONGODB_DB_NAME: str = os.getenv("MONGODB_DB_NAME", "biomindq")
    GROQ_API_KEY: Optional[str] = os.getenv("GROQ_API_KEY", "")
    NCBI_API_KEY: Optional[str] = os.getenv("NCBI_API_KEY", "")
    DRUGBANK_API_KEY: Optional[str] = os.getenv("DRUGBANK_API_KEY", "")
    JWT_SECRET: str = os.getenv("JWT_SECRET", "biomindq_super_secret_jwt_key_2026_safe_hash")
    PINECONE_API_KEY: Optional[str] = os.getenv("PINECONE_API_KEY", "")
    PINECONE_INDEX_NAME: str = os.getenv("PINECONE_INDEX_NAME", "biomindq-sessions")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
