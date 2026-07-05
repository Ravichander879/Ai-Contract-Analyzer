from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class ContractUploadResponse(BaseModel):
    contract_id: str
    filename: str
    pages: int
    size_kb: float

class KeyClauseSchema(BaseModel):
    name: str
    description: str
    interpretation: str
    page: Optional[Any] = None

class RiskyClauseSchema(BaseModel):
    name: str
    risk_level: str
    confidence: Optional[Any] = None
    description: str
    recommendation: str
    page: Optional[Any] = None

class AnalysisResponse(BaseModel):
    summary: str
    risk_score: int
    key_clauses: List[KeyClauseSchema]
    risky_clauses: List[RiskyClauseSchema]
    analysis_time: Optional[float] = None

class ChatRequest(BaseModel):
    question: str

class ChatResponse(BaseModel):
    answer: str
    context: List[Dict[str, Any]]
