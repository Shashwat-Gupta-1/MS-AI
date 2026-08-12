"""
agent/state.py — LangGraph State schema definition.
Every node in the state graph receives and updates this TypedDict.
"""

from typing import TypedDict, List, Dict, Any, Optional
import pandas as pd


class GraphState(TypedDict, total=False):
    # Context & User Identity
    user_id: str
    role: str
    session_id: str
    question: str
    output_mode: str          # "exact" | "summary"
    
    # Router Decision
    case_type: str            # "case_a" | "case_b" | "case_c"
    router_reason: str
    
    # Guardrail Check
    is_valid_intent: bool
    guardrail_reason: Optional[str]
    
    # Domain & Role Access
    allowed_domains: List[str]
    keyword_matched_domains: List[str]
    llm_matched_domains: List[str]
    final_domains: List[str]
    
    # Schema & Retrieval
    retrieved_tables: List[str]
    join_paths: List[Dict[str, Any]]
    schema_context: str
    
    # Column-Level Embedding & Schema Retrieval
    anchor_tables: List[str]
    candidate_columns: List[Dict[str, Any]]
    reranked_columns: List[Dict[str, Any]]
    connecting_tables: List[str]
    propagated_filters: List[Dict[str, Any]]
    schema_trim_log: Optional[Dict[str, Any]]
    schema_retrieval_mode: str

    
    # SQL Generation & Validation
    sql_query: Optional[str]
    validation_attempts: int
    is_sql_valid: bool
    validation_error_object: Optional[Dict[str, Any]]  # {rule_violated, detail, offending_sql_fragment}
    
    # Query Execution & Results
    query_records: Optional[List[Dict[str, Any]]]
    query_columns: Optional[List[str]]
    final_response: Any        # List[Dict[str, Any]] (for exact) or str (for summary)
    bytes_processed: int
    execution_time_ms: float

    
    # Error Handling & Flow Control
    status: str               # "running" | "completed" | "rejected" | "error"
    error_message: Optional[str]
