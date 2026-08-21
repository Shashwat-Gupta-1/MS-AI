"""
agent/nodes/router.py — Node [0]: Conversation Router Agent.
Evaluates prior session turn history, user prompt, and time-gap signal to classify
the request as Case A (New Chat), Case B (Follow-up), or Case C (Topic Shift).
"""

import time
from typing import Dict, Any, List
from langchain_core.messages import SystemMessage, HumanMessage

from config_guardrails import FOLLOWUP_TIME_GAP_THRESHOLD_SECONDS

from agent.state import GraphState
from agent.session_store import DEFAULT_SESSION_STORE
from agent.groq_client import invoke_groq_with_retry
from agent.logging_store import DEFAULT_LOGGING_STORE

ROUTER_SYSTEM_PROMPT = """You are a conversation flow router for a financial data analytics assistant.
Your job is to determine whether the user's latest question is a direct follow-up / refinement of the immediately preceding conversation turn, or a completely new, unrelated topic.

PRIOR CONVERSATION HISTORY:
{history_text}

LATEST USER QUESTION:
{question}

Classify into one of two options:
- FOLLOW_UP: The question relies on context, filters, or entities from the prior turn (e.g. "now break that down by branch", "what about last month?", "show me just gold loans").If the new question is identical or highly similar to the previous question, also classify it as a FOLLOW_UP to reuse the existing context.
- NEW_TOPIC: The question introduces a completely new topic or query independent of previous turns.

Respond with EXACTLY two lines:
Line 1: FOLLOW_UP or NEW_TOPIC
Line 2: Brief explanation of your decision
"""


def router_node(state: GraphState) -> Dict[str, Any]:
    """LangGraph entry node routing query across Case A, Case B, and Case C."""
    start_time = time.time()
    user_id = state.get("user_id", "default_user")
    session_id = state.get("session_id", "default_session")
    role = state.get("role", "unknown")
    question = state.get("question", "")
    
    session = DEFAULT_SESSION_STORE.get_session(user_id, session_id)
    turns = session.get("turns", [])
    
    # Case A: No prior turns exist in session
    if not turns:
        res = {
            "case_type": "case_a",
            "router_reason": "No prior turns in session. Fresh conversation pipeline.",
        }
        DEFAULT_LOGGING_STORE.log_stage(
            session_id=session_id,
            role=role,
            turn_index=len(turns) + 1,
            stage="router",
            input_data=question,
            output_data="case_a",
            success=True,
            latency_ms=(time.time() - start_time) * 1000,
            extra_fields={"chosen_case": "case_a", "fallback_used": False},
        )
        return res

    # Time-gap fallback pre-check
    last_ts = session.get("last_active_at", time.time())
    time_gap_seconds = time.time() - last_ts
    fallback_used = False
    
    # Format prior turns history for LLM
    history_lines = []
    for idx, t in enumerate(turns[-3:]):
        history_lines.append(f"Turn {idx+1}: {t.get('question')}")
        if t.get("matched_domains"):
            history_lines.append(f"  Domains: {', '.join(t.get('matched_domains'))}")
    history_text = "\n".join(history_lines) if history_lines else "None"
    
    prompt = ROUTER_SYSTEM_PROMPT.format(history_text=history_text, question=question)
    messages = [
        SystemMessage(content="You are a conversation flow router node for MSAI analytics."),
        HumanMessage(content=prompt),
    ]

    
    try:
        response = invoke_groq_with_retry(messages, temperature=0.0)
        meta = getattr(response, "response_metadata", {}) or {}
        llm_model = meta.get("model_name")
        tokens_used = meta.get("token_usage")
        lines = response.content.strip().split("\n")
        decision_line = lines[0].strip().upper()
        reason = lines[1].strip() if len(lines) > 1 else "No explanation provided."
        
        is_followup = "FOLLOW_UP" in decision_line
        
        # Apply time-gap fallback threshold override
        if is_followup and time_gap_seconds > FOLLOWUP_TIME_GAP_THRESHOLD_SECONDS:
            is_followup = False
            fallback_used = True
            reason += f" (Overridden to Case C due to time gap of {int(time_gap_seconds)}s > {FOLLOWUP_TIME_GAP_THRESHOLD_SECONDS}s)"

        if is_followup:
            # Case B: Follow-up question -- carried forward context from prior turn
            active_domains = session.get("active_domains", [])
            active_tables = session.get("active_tables", [])
            active_schema = session.get("active_schema_context", "")
            last_turn = turns[-1] if turns else {}
            
            res = {
                "case_type": "case_b",
                "router_reason": reason,
                "final_domains": active_domains,
                "retrieved_tables": active_tables,
                "schema_context": active_schema,
                "prior_question": last_turn.get("question"),
                "prior_sql": last_turn.get("sql_query"),
            }
            chosen_case = "case_b"
        else:
            # Case C: New topic in existing session
            res = {
                "case_type": "case_c",
                "router_reason": reason,
            }
            chosen_case = "case_c"
            
        DEFAULT_LOGGING_STORE.log_stage(
            session_id=session_id,
            role=role,
            turn_index=len(turns) + 1,
            stage="router",
            input_data={"question": question, "time_gap_seconds": time_gap_seconds},
            output_data=chosen_case,
            success=True,
            latency_ms=(time.time() - start_time) * 1000,
            llm_model=llm_model,
            tokens_used=tokens_used,
            extra_fields={
                "chosen_case": chosen_case,
                "router_reason": reason,
                "fallback_used": fallback_used,
            },
        )
        return res


    except Exception as e:
        # Safety fallback to Case C on router error
        err_reason = f"Router LLM error: {str(e)}. Defaulting to Case C full pipeline."
        res = {
            "case_type": "case_c",
            "router_reason": err_reason,
        }
        DEFAULT_LOGGING_STORE.log_stage(
            session_id=session_id,
            role=role,
            turn_index=len(turns) + 1,
            stage="router",
            input_data=question,
            output_data="case_c",
            success=False,
            failure_reason=err_reason,
            latency_ms=(time.time() - start_time) * 1000,
            extra_fields={"chosen_case": "case_c", "fallback_used": True},
        )
        return res
