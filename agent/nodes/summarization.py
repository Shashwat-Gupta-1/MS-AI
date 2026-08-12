"""
agent/nodes/summarization.py — Node [7]: Chunked Map-Reduce Summarizer Agent.
Implements memory-safe Map-Reduce summarization over raw query DataFrames:
1. Splits DataFrame into row chunks (e.g. 200 rows per chunk).
2. Map Pass: Groq extracts partial summaries / key business points per chunk.
3. Reduce Pass: Groq synthesizes final executive bullet points from partial summaries.
"""

import time
import pandas as pd
from typing import Dict, Any, List
from langchain_core.messages import SystemMessage, HumanMessage

from config_guardrails import SUMMARIZATION_CHUNK_ROW_SIZE

from agent.state import GraphState
from agent.groq_client import invoke_groq_with_retry
from agent.logging_store import DEFAULT_LOGGING_STORE

CHUNK_MAP_PROMPT = """You are a financial data analyst summarizing tabular query results.
Analyze the following data chunk (Rows {start_row} to {end_row}) to answer the user's question: "{question}"

Data Chunk:
{chunk_csv}

Extract key numeric insights, trends, outliers, totals, or averages relevant to the question.
Output concise bullet points summarizing this chunk ONLY. Do NOT output raw CSV rows verbatim.
"""

FINAL_REDUCE_PROMPT = """You are an executive assistant preparing a final business summary for an NBFC manager.
Combine the following partial key-point summaries into a clear, professional, executive bulleted response to answer: "{question}"

Partial Key-Point Summaries:
{combined_summaries}

Provide a well-structured final answer with bullet points, highlighting key numbers and key business takeaways.
"""

SINGLE_PASS_PROMPT = """You are a financial data analyst summarizing query results for an executive manager.
Question: "{question}"

Data Results ({total_rows} rows):
{data_csv}

Provide a concise, professional executive summary with clear bullet points highlighting key metrics, totals, averages, or top findings.
"""


def generate_fallback_bullet_summary(df: pd.DataFrame, question: str) -> str:
    """Deterministic fallback summarizer generating clean bullet points directly from DataFrame metrics."""
    total_rows = len(df)
    cols = list(df.columns)
    
    bullets = [
        f"**Query Results Summary ({total_rows} records returned):**",
        f"- **Attributes Analyzed:** {', '.join(cols[:6])}",
    ]
    
    # Calculate numeric stats for numeric columns
    numeric_cols = df.select_dtypes(include=["number"]).columns
    for c in numeric_cols[:4]:
        val_sum = df[c].sum()
        val_avg = df[c].mean()
        bullets.append(f"- **Total {c}:** `{val_sum:,.2f}` (Average: `{val_avg:,.2f}`)")
        
    # Include sample rows
    bullets.append("\n**Key Records Preview:**")
    for idx, row in df.head(5).iterrows():
        row_str = ", ".join([f"{k}: `{v}`" for k, v in row.items() if pd.notna(v)])
        bullets.append(f"- Row {idx + 1}: {row_str}")
        
    return "\n".join(bullets)


def summarize_chunk_map_pass(
    df_chunk: pd.DataFrame,
    question: str,
    start_row: int,
    end_row: int,
):
    """Map Pass: Extract key points from a single row chunk."""
    chunk_csv = df_chunk.to_csv(index=False)
    prompt = CHUNK_MAP_PROMPT.format(
        start_row=start_row,
        end_row=end_row,
        question=question,
        chunk_csv=chunk_csv,
    )
    messages = [HumanMessage(content=prompt)]
    response = invoke_groq_with_retry(messages, temperature=0.2)
    meta = getattr(response, "response_metadata", {}) or {}
    return response.content.strip(), meta.get("model_name"), meta.get("token_usage")


def summarize_reduce_pass(
    partial_summaries: List[str],
    question: str,
):
    """Reduce Pass: Synthesize final coherent executive summary from partial points."""
    combined_text = "\n\n".join([f"--- Chunk {i+1} Summary ---\n{s}" for i, s in enumerate(partial_summaries)])
    prompt = FINAL_REDUCE_PROMPT.format(
        question=question,
        combined_summaries=combined_text,
    )
    messages = [HumanMessage(content=prompt)]
    response = invoke_groq_with_retry(messages, temperature=0.2)
    meta = getattr(response, "response_metadata", {}) or {}
    return response.content.strip(), meta.get("model_name"), meta.get("token_usage")


def summarization_node(state: GraphState) -> Dict[str, Any]:
    """LangGraph node executing Map-Reduce or Single-Pass summarization when output_mode='summary'."""
    start_time = time.time()
    session_id = state.get("session_id", "default")
    role = state.get("role", "unknown")
    question = state.get("question", "")
    records = state.get("query_records")
    output_mode = state.get("output_mode", "exact")
    
    # If not in summary mode or no records, return immediately
    if output_mode != "summary" or records is None:
        return {}
        
    df = pd.DataFrame(records)
    if df.empty:
        res = {
            "final_response": "The query executed successfully but returned 0 matching records.",
            "status": "completed",
        }
        DEFAULT_LOGGING_STORE.log_stage(
            session_id=session_id,
            role=role,
            turn_index=0,
            stage="summarization_map",
            input_data=question,
            output_data="Empty DataFrame",
            success=True,
            latency_ms=(time.time() - start_time) * 1000,
        )
        return res
        
    total_rows = len(df)
    
    try:
        # Optimization: Single-Pass for small result sets (<= 50 rows)
        if total_rows <= 50:
            prompt = SINGLE_PASS_PROMPT.format(
                question=question,
                total_rows=total_rows,
                data_csv=df.to_csv(index=False),
            )
            response = invoke_groq_with_retry([HumanMessage(content=prompt)], temperature=0.2)
            final_summary = response.content.strip()
            meta = getattr(response, "response_metadata", {}) or {}
            
            DEFAULT_LOGGING_STORE.log_stage(
                session_id=session_id,
                role=role,
                turn_index=0,
                stage="summarization_single_pass",
                input_data={"total_rows": total_rows},
                output_data=final_summary,
                success=True,
                latency_ms=(time.time() - start_time) * 1000,
                llm_model=meta.get("model_name"),
                tokens_used=meta.get("token_usage"),
            )
            return {"final_response": final_summary, "status": "completed"}
            
        # Multi-Chunk Map-Reduce for large result sets (> 50 rows)
        chunk_size = SUMMARIZATION_CHUNK_ROW_SIZE
        partial_summaries = []
        
        for i in range(0, total_rows, chunk_size):
            chunk_df = df.iloc[i : i + chunk_size]
            start_row = i + 1
            end_row = min(i + chunk_size, total_rows)
            
            c_start_time = time.time()
            p_summary, c_model, c_tokens = summarize_chunk_map_pass(chunk_df, question, start_row, end_row)
            partial_summaries.append(p_summary)
            
            DEFAULT_LOGGING_STORE.log_stage(
                session_id=session_id,
                role=role,
                turn_index=0,
                stage="summarization_chunk",
                input_data={"start_row": start_row, "end_row": end_row},
                output_data=p_summary,
                success=True,
                latency_ms=(time.time() - c_start_time) * 1000,
                llm_model=c_model,
                tokens_used=c_tokens,
            )

        r_start_time = time.time()
        final_summary, r_model, r_tokens = summarize_reduce_pass(partial_summaries, question)
        
        DEFAULT_LOGGING_STORE.log_stage(
            session_id=session_id,
            role=role,
            turn_index=0,
            stage="summarization_reduce",
            input_data={"chunk_count": len(partial_summaries)},
            output_data=final_summary,
            success=True,
            latency_ms=(time.time() - r_start_time) * 1000,
            llm_model=r_model,
            tokens_used=r_tokens,
        )
        return {"final_response": final_summary, "status": "completed"}
        
    except Exception as e:
        # Fail-Safe Fallback: Generate bullet points directly from DataFrame stats
        fallback_summary = generate_fallback_bullet_summary(df, question)
        DEFAULT_LOGGING_STORE.log_stage(
            session_id=session_id,
            role=role,
            turn_index=0,
            stage="summarization_fallback",
            input_data=str(e),
            output_data=fallback_summary,
            success=False,
            failure_reason=str(e),
            latency_ms=(time.time() - start_time) * 1000,
        )
        return {"final_response": fallback_summary, "status": "completed"}


