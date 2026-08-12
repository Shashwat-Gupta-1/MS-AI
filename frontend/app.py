"""
frontend/app.py — Streamlit UI application for MSAI Chatbot.
Provides interactive analyst dashboard with role selection, chat thread history,
prompt input with dual output-mode buttons ('Get Exact Data' & 'Get Summary'),
collapsible SQL view, dry-run cost indicators, and formatted result rendering.
"""

import sys
import uuid
import time
from pathlib import Path
import streamlit as st
import pandas as pd

# Add repo root to sys.path so imports resolve cleanly
REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT))

from agent.graph import app_graph
from agent.session_store import DEFAULT_SESSION_STORE
try:
    from agent.nodes.domain_match import ROLE_ACCESS_MAP
except ImportError:
    ROLE_ACCESS_MAP = {}


# Page Configuration
st.set_page_config(
    page_title="MSAI — Financial Data Chatbot",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded",
)


def init_session_state():
    """Initialize Streamlit session state keys."""
    if "user_id" not in st.session_state:
        st.session_state.user_id = "analyst_user_01"
    if "role" not in st.session_state:
        st.session_state.role = "executive"
    if "current_session_id" not in st.session_state:
        st.session_state.current_session_id = str(uuid.uuid4())[:8]
    if "sessions" not in st.session_state:
        st.session_state.sessions = [st.session_state.current_session_id]
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = {}  # session_id -> list of message dicts


init_session_state()

# -----------------------------
# SIDEBAR
# -----------------------------
st.sidebar.title("🏦 MSAI Analytics")
st.sidebar.caption("Natural Language RAG over BigQuery Warehouse")

# User ID Input
st.sidebar.subheader("User Identity")
user_id_input = st.sidebar.text_input("User ID", value=st.session_state.user_id)
if user_id_input != st.session_state.user_id:
    st.session_state.user_id = user_id_input

# Role Selection Dropdown
roles_list = [
    "executive",
    "loan_officer",
    "collections_agent",
    "hr_officer",
    "sales_rep",
    "branch_manager",
    "compliance_officer",
    "treasury_manager",
    "insurance_ops",
    "support_agent",
]

selected_role = st.sidebar.selectbox(
    "Role",
    options=roles_list,
    index=roles_list.index(st.session_state.role) if st.session_state.role in roles_list else 0,
    help="Determines domain access boundaries and view dataset permissions.",
)
if selected_role != st.session_state.role:
    st.session_state.role = selected_role

st.sidebar.divider()

# Session Manager
st.sidebar.subheader("Chat Threads")
if st.sidebar.button("➕ New Chat", use_container_width=True):
    new_id = str(uuid.uuid4())[:8]
    st.session_state.sessions.append(new_id)
    st.session_state.current_session_id = new_id
    st.rerun()

session_options = st.session_state.sessions[::-1]
current_session = st.sidebar.radio(
    "Select Session",
    options=session_options,
    index=session_options.index(st.session_state.current_session_id),
    format_func=lambda s: f"Chat Thread #{s}",
)
if current_session != st.session_state.current_session_id:
    st.session_state.current_session_id = current_session
    st.rerun()


# -----------------------------
# MAIN CHAT AREA
# -----------------------------
st.title("📊 Financial Data Analyst Assistant")
st.caption(f"Active Role: `{st.session_state.role}` | Target Dataset: `views_{st.session_state.role}` | Session: `#{st.session_state.current_session_id}`")

active_session_id = st.session_state.current_session_id
if active_session_id not in st.session_state.chat_history:
    st.session_state.chat_history[active_session_id] = []

messages = st.session_state.chat_history[active_session_id]

# Render past chat messages in active session
for msg in messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["text"])
        if "sql" in msg and msg["sql"]:
            with st.expander("🔍 View Generated BigQuery SQL"):
                st.code(msg["sql"], language="sql")
                if "bytes_processed" in msg:
                    mb = msg["bytes_processed"] / (1024 * 1024)
                    st.caption(f"Estimated Scan: {mb:.2f} MB")
        if "dataframe" in msg and msg["dataframe"] is not None:
            st.dataframe(msg["dataframe"], use_container_width=True)

# -----------------------------
# DUAL BUTTON INPUT BAR
# -----------------------------
st.divider()

with st.container():
    prompt_input = st.text_input("Ask a question about loans, collections, HR, leads, treasury, etc.:", key="prompt_box")
    
    col1, col2, col3 = st.columns([1, 1, 3])
    with col1:
        btn_exact = st.button("📊 Get Exact Data", type="primary", use_container_width=True)
    with col2:
        btn_summary = st.button("💡 Get Summary", type="secondary", use_container_width=True)

output_mode = None
if btn_exact:
    output_mode = "exact"
elif btn_summary:
    output_mode = "summary"

if output_mode and prompt_input.strip():
    question_text = prompt_input.strip()
    
    # 1. Append user prompt to chat UI
    st.session_state.chat_history[active_session_id].append({
        "role": "user",
        "text": question_text,
    })
    
    with st.chat_message("user"):
        st.markdown(question_text)

    # 2. Invoke LangGraph Pipeline
    with st.chat_message("assistant"):
        with st.spinner("Processing request through guardrails & retrieval graph..."):
            
            initial_state = {
                "user_id": st.session_state.user_id,
                "role": st.session_state.role,
                "session_id": active_session_id,
                "question": question_text,
                "output_mode": output_mode,
                "validation_attempts": 0,
            }
            
            thread_config = {
                "configurable": {
                    "thread_id": f"{st.session_state.user_id}:{active_session_id}"
                }
            }
            
            try:
                final_state = app_graph.invoke(initial_state, config=thread_config)
                
                status = final_state.get("status")
                response = final_state.get("final_response")
                sql = final_state.get("sql_query")
                bytes_p = final_state.get("bytes_processed", 0)
                raw_df = final_state.get("raw_dataframe")
                case_type = final_state.get("case_type")

                # Display Routing Info
                if case_type:
                    st.caption(f"⚡ Pipeline Route: `{case_type.upper()}`")

                # Render SQL Expander if query was generated
                if sql:
                    with st.expander("🔍 View Generated BigQuery SQL"):
                        st.code(sql, language="sql")
                        if bytes_p:
                            st.caption(f"BigQuery Dry-Run Scan: {bytes_p / (1024*1024):.2f} MB")

                # Render Response
                records = final_state.get("query_records")
                if isinstance(response, str):
                    if status in ["rejected", "error", "failed"]:
                        st.error(response)
                    else:
                        st.markdown(response)

                    st.session_state.chat_history[active_session_id].append({
                        "role": "assistant",
                        "text": response,
                        "sql": sql,
                        "bytes_processed": bytes_p,
                        "dataframe": None,
                    })
                elif isinstance(response, list) or (output_mode == "exact" and records):
                    rec_list = response if isinstance(response, list) else records
                    df = pd.DataFrame(rec_list)
                    st.success(f"Query returned {len(df)} records.")
                    st.dataframe(df, use_container_width=True)
                    st.session_state.chat_history[active_session_id].append({
                        "role": "assistant",
                        "text": f"Table output with {len(df)} rows:",
                        "sql": sql,
                        "bytes_processed": bytes_p,
                        "dataframe": df,
                    })
                else:
                    st.warning("No output returned.")

                    
            except Exception as e:
                err_msg = f"Graph Execution Error: {str(e)}"
                st.error(err_msg)
                st.session_state.chat_history[active_session_id].append({
                    "role": "assistant",
                    "text": err_msg,
                    "sql": None,
                    "dataframe": None,
                })
