from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class HealthResponse(BaseModel):
    mongo: str
    groq: str

class QueryRequest(BaseModel):
    question: str = Field(..., description="Plain language biomedical research question")

class PlannerOutput(BaseModel):
    intent: str = Field(default="database_search", description="database_search | direct_answer")
    reasoning: str = Field(default="", description="Reasoning for query intent classification")
    sources: List[str] = Field(default_factory=list, description="Selected data sources e.g. pubmed, chembl, pubchem, drugbank")
    per_source_query: Dict[str, str] = Field(default_factory=dict, description="Queries formatted per source")

class EntityLink(BaseModel):
    entity: str
    sources: List[str]

class ItemStance(BaseModel):
    item_id: str
    source: str
    stance: str = Field(default="supports", description="supports | contradicts | mentions")

class VerifierOutput(BaseModel):
    entities_linked: List[EntityLink] = Field(default_factory=list)
    agreements: List[str] = Field(default_factory=list)
    conflicts: List[str] = Field(default_factory=list)
    confidence: int = Field(default=0, ge=0, le=100)
    item_stances: List[ItemStance] = Field(default_factory=list)

class ConsensusMeter(BaseModel):
    label: str = Field(default="Strong Consensus", description="Strong Consensus | Mostly Supported | Mixed Evidence | Conflicting | Direct Response")
    supports: int = 0
    contradicts: int = 0
    mentions: int = 0
    total_sources: int = 0

class EvidenceItem(BaseModel):
    claim: str
    source: str
    url: str
    stance: str = Field(default="SUPPORTS", description="SUPPORTS | CONTRASTS | MENTIONS")

class FinalAnswer(BaseModel):
    retrieved_evidence: List[EvidenceItem] = Field(default_factory=list)
    ai_summary: str
    confidence_score: int = Field(default=0, ge=0, le=100)
    disclaimer: str = "Research and informational tool only — not intended for diagnosis or treatment."

class QueryResponse(BaseModel):
    final_answer: FinalAnswer
    verifier_output: VerifierOutput
    consensus: ConsensusMeter
    latency_ms: float
