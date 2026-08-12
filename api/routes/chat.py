"""
api/routes/chat.py — Thin FastAPI route wrapper invoking the LangGraph pipeline.
"""

import time
import uuid
from typing import Tuple
from fastapi import APIRouter, Depends, HTTPException, status


from agent.graph import app_graph
from agent.session_store import SessionStore
from agent.logging_store import LoggingStore
from api.schemas import ChatRequest, ChatResponse, SessionHistoryResponse, SessionTurn
from api.deps import get_current_user_and_role, get_session_store, get_logging_store

router = APIRouter(prefix="/api/v1", tags=["Chat & Sessions"])


@router.post("/chat", response_model=ChatResponse)
async def post_chat(
    req: ChatRequest,
    user_and_role: Tuple[str, str] = Depends(get_current_user_and_role),
    session_store: SessionStore = Depends(get_session_store),
    logging_store: LoggingStore = Depends(get_logging_store),
):
    """
    POST /chat — Submit analytical question to the multi-agent graph pipeline.
    Role is resolved server-side from auth token (never client request body).
    """
    start_time = time.time()
    user_id, role = user_and_role
    session_id = req.session_id or f"session_{uuid.uuid4().hex[:8]}"

    initial_state = {
        "user_id": user_id,
        "role": role,
        "session_id": session_id,
        "question": req.question,
        "output_mode": req.output_mode,
        "validation_attempts": 0,
    }

    config = {
        "configurable": {
            "thread_id": f"{user_id}:{session_id}"
        }
    }

    try:
        # Non-blocking async invocation of compiled LangGraph
        final_state = await app_graph.ainvoke(initial_state, config=config)
    except Exception as e:
        latency_ms = (time.time() - start_time) * 1000
        logging_store.log_stage(
            session_id=session_id,
            role=role,
            turn_index=0,
            stage="api_boundary",
            input_data=req.question,
            output_data=f"Unhandled API Error: {str(e)}",
            success=False,
            failure_reason=str(e),
            latency_ms=latency_ms,
        )
        raise HTTPException(
            status_code=500,
            detail=f"LangGraph execution error: {str(e)}",
        )

    latency_ms = (time.time() - start_time) * 1000

    # API boundary logging
    logging_store.log_stage(
        session_id=session_id,
        role=role,
        turn_index=0,
        stage="api_boundary",
        input_data=req.question,
        output_data={"status": final_state.get("status"), "latency_ms": latency_ms},
        success=(final_state.get("status") == "completed"),
        failure_reason=final_state.get("error_message"),
        latency_ms=latency_ms,
    )

    # Response payload assembly
    status_str = final_state.get("status", "completed")
    resp_body = final_state.get("final_response")
    if resp_body is None:
        resp_body = final_state.get("error_message") or final_state.get("guardrail_reason") or "No response generated."

    return ChatResponse(
        session_id=session_id,
        user_id=user_id,
        role=role,
        status=status_str,
        case_type=final_state.get("case_type"),
        final_response=resp_body,
        sql_query=final_state.get("sql_query"),
        matched_domains=final_state.get("final_domains", []),
        retrieved_tables=final_state.get("retrieved_tables", []),
        bytes_processed=final_state.get("bytes_processed", 0),
        execution_time_ms=final_state.get("execution_time_ms", 0.0),
        latency_ms=latency_ms,
    )


@router.get("/sessions/{session_id}", response_model=SessionHistoryResponse)
async def get_session_history(
    session_id: str,
    user_and_role: Tuple[str, str] = Depends(get_current_user_and_role),
    session_store: SessionStore = Depends(get_session_store),
):
    """
    GET /sessions/{session_id} — Retrieve turn history for an active session.
    Reads via shared SessionStore interface.
    """
    user_id, role = user_and_role
    session_data = session_store.get_session(user_id, session_id)
    
    if not session_data or not session_data.get("turns"):
        raise HTTPException(
            status_code=404,
            detail=f"Session '{session_id}' not found for user '{user_id}'.",
        )

    turns = [
        SessionTurn(
            timestamp=t.get("timestamp", 0.0),
            question=t.get("question", ""),
            sql_query=t.get("sql_query"),
            matched_domains=t.get("matched_domains", []),
            retrieved_tables=t.get("retrieved_tables", []),
        )
        for t in session_data.get("turns", [])
    ]

    return SessionHistoryResponse(
        session_id=session_id,
        user_id=user_id,
        role=role,
        created_at=session_data.get("created_at", 0.0),
        last_active_at=session_data.get("last_active_at", 0.0),
        turns=turns,
    )
