"""
agent/graph.py — Assembles and compiles the multi-agent LangGraph StateGraph.
Connects router, guardrail, domain_match, retrieval, sql_generation, query_validation,
execution, and summarization nodes with conditional routing logic and retry loops.
"""

from typing import Dict, Any, Literal
from langgraph.graph import StateGraph, END

from config_guardrails import MAX_VALIDATION_RETRIES

from agent.state import GraphState
from agent.session_store import DEFAULT_SESSION_STORE, DEFAULT_SESSION_STORE
from agent.nodes.router import router_node
from agent.nodes.guardrail import guardrail_node
from agent.nodes.domain_match import domain_match_node
from agent.nodes.retrieval import retrieval_node
from agent.nodes.sql_generation import sql_generation_node
from agent.nodes.query_validation import query_validation_node
from agent.nodes.execution import execution_node
from agent.nodes.summarization import summarization_node


from agent.nodes.schema_retrieval import schema_retrieval_node


def session_turn_saver_node(state: GraphState) -> Dict[str, Any]:
    """Helper node persisting completed turn context into session store."""
    user_id = state.get("user_id", "default_user")
    session_id = state.get("session_id", "default_session")
    question = state.get("question", "")
    sql = state.get("sql_query")
    response = state.get("final_response")
    domains = state.get("final_domains", [])
    tables = state.get("retrieved_tables", [])
    
    DEFAULT_SESSION_STORE.append_turn(
        user_id=user_id,
        session_id=session_id,
        question=question,
        sql_query=sql,
        final_response=response,
        matched_domains=domains,
        retrieved_tables=tables,
    )
    return {"status": "completed"}


# Conditional Routing Functions

def route_after_router(state: GraphState) -> Literal["sql_generation", "guardrail"]:
    """Case B (Follow-up) skips domain match & retrieval directly to SQL generation."""
    case_type = state.get("case_type", "case_a")
    if case_type == "case_b":
        return "sql_generation"
    return "guardrail"


def route_after_guardrail(state: GraphState) -> Literal["domain_match", "__end__"]:
    """Stop graph execution immediately if input guardrail rejects question."""
    if not state.get("is_valid_intent", True):
        return END
    return "domain_match"


def route_after_domain_match(state: GraphState) -> Literal["retrieval", "__end__"]:
    """Stop graph execution if domain access validation fails."""
    if state.get("status") == "rejected":
        return END
    return "retrieval"


def route_after_validation(state: GraphState) -> Literal["execution", "sql_generation", "__end__"]:
    """
    Self-correction loop:
    - If valid -> proceed to execution.
    - If invalid and attempts < MAX_VALIDATION_RETRIES -> loop back to sql_generation.
    - If attempts >= MAX_VALIDATION_RETRIES -> terminate graph.
    """
    if state.get("is_sql_valid", False):
        return "execution"
        
    attempts = state.get("validation_attempts", 1)
    if attempts < MAX_VALIDATION_RETRIES and state.get("status") != "failed":
        return "sql_generation"
        
    return END


def route_after_execution(state: GraphState) -> Literal["summarization", "session_turn_saver", "__end__"]:
    """Route to summarization if output_mode='summary', else directly save turn."""
    if state.get("status") in ["error", "rejected"]:
        return END
        
    if state.get("output_mode") == "summary":
        return "summarization"
        
    return "session_turn_saver"


def build_app_graph():
    """Build and compile the LangGraph StateGraph workflow."""
    workflow = StateGraph(GraphState)
    
    # Register Nodes
    workflow.add_node("router", router_node)
    workflow.add_node("guardrail", guardrail_node)
    workflow.add_node("domain_match", domain_match_node)
    workflow.add_node("retrieval", retrieval_node)
    workflow.add_node("schema_retrieval", schema_retrieval_node)
    workflow.add_node("sql_generation", sql_generation_node)
    workflow.add_node("query_validation", query_validation_node)
    workflow.add_node("execution", execution_node)
    workflow.add_node("summarization", summarization_node)
    workflow.add_node("session_turn_saver", session_turn_saver_node)
    
    # Wire Edges & Conditional Routing
    workflow.set_entry_point("router")
    
    workflow.add_conditional_edges("router", route_after_router)
    workflow.add_conditional_edges("guardrail", route_after_guardrail)
    workflow.add_conditional_edges("domain_match", route_after_domain_match)
    
    # Advisory sequencing: retrieval -> schema_retrieval -> sql_generation
    workflow.add_edge("retrieval", "schema_retrieval")
    workflow.add_edge("schema_retrieval", "sql_generation")
    workflow.add_edge("sql_generation", "query_validation")

    
    workflow.add_conditional_edges("query_validation", route_after_validation)
    workflow.add_conditional_edges("execution", route_after_execution)
    
    workflow.add_edge("summarization", "session_turn_saver")
    workflow.add_edge("session_turn_saver", END)
    
    # Compile with MemorySaver checkpointer
    app_graph = workflow.compile(checkpointer=DEFAULT_SESSION_STORE.checkpointer)
    return app_graph


# Pre-compiled global graph instance
app_graph = build_app_graph()
