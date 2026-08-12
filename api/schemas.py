"""
api/schemas.py — Pydantic request and response models for MSAI FastAPI endpoints.
"""

from typing import List, Dict, Any, Optional, Literal
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, description="Analytical query text asked by user.")
    session_id: Optional[str] = Field(None, description="Optional existing session ID to append query to.")
    output_mode: Literal["exact", "summary"] = Field("exact", description="Format output: 'exact' (tabular data) or 'summary' (bulleted insights).")


class ChatResponse(BaseModel):
    session_id: str = Field(..., description="Active session ID for conversation continuity.")
    user_id: str = Field(..., description="Authenticated user ID.")
    role: str = Field(..., description="Authenticated role enforced by server-side lookup.")
    status: str = Field(..., description="Pipeline execution status ('completed', 'rejected', 'error').")
    case_type: Optional[str] = Field(None, description="Conversation routing decision ('case_a', 'case_b', 'case_c').")
    final_response: Any = Field(..., description="Execution response payload: list of records or summary string.")
    sql_query: Optional[str] = Field(None, description="Generated and validated BigQuery SQL statement.")
    matched_domains: List[str] = Field(default_factory=list, description="Domains identified for this turn.")
    retrieved_tables: List[str] = Field(default_factory=list, description="Shortlisted database views.")
    bytes_processed: int = Field(0, description="BigQuery dry-run scan size in bytes.")
    execution_time_ms: float = Field(0.0, description="LangGraph pipeline internal execution latency in ms.")
    latency_ms: float = Field(0.0, description="Full HTTP request-to-response round-trip latency in ms.")


class SessionTurn(BaseModel):
    timestamp: float
    question: str
    sql_query: Optional[str] = None
    matched_domains: List[str] = Field(default_factory=list)
    retrieved_tables: List[str] = Field(default_factory=list)


class SessionHistoryResponse(BaseModel):
    session_id: str
    user_id: str
    role: str
    created_at: float
    last_active_at: float
    turns: List[SessionTurn] = Field(default_factory=list)
