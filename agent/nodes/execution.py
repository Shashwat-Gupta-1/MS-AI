"""
agent/nodes/execution.py — Node [6]: Role-Scoped Query Execution Agent.
Executes validated BigQuery SQL against views_<role>.* datasets using
get_client_for_role(role). Enforces maximum row caps on execution results.
"""

import time
from typing import Dict, Any
from google.cloud.bigquery import QueryJobConfig

from config_guardrails import MAX_ROW_COUNT_CAP

from agent.state import GraphState
from agent.logging_store import DEFAULT_LOGGING_STORE
from bq_client import get_client_for_role


def execution_node(state: GraphState) -> Dict[str, Any]:
    """LangGraph node executing validated SQL under role credentials."""
    start_time = time.time()
    session_id = state.get("session_id", "default")
    role = state.get("role", "unknown")
    sql = state.get("sql_query", "")
    output_mode = state.get("output_mode", "exact")
    
    if not sql:
        res = {
            "status": "error",
            "final_response": "No SQL query available to execute.",
        }
        return res
        
    client = get_client_for_role(role)
    
    try:
        query_job = client.query(sql)
        df = query_job.to_dataframe(max_results=MAX_ROW_COUNT_CAP)
        
        exec_latency = (time.time() - start_time) * 1000
        records = df.to_dict(orient="records")
        cols = list(df.columns)
        
        res = {
            "query_records": records,
            "query_columns": cols,
            "execution_time_ms": exec_latency,
        }
        
        # If output mode is exact data, format response
        if output_mode == "exact":
            res["final_response"] = records
            res["status"] = "completed"
            
        DEFAULT_LOGGING_STORE.log_stage(
            session_id=session_id,
            role=role,
            turn_index=0,
            stage="execution",
            input_data=sql,
            output_data={"row_count": len(records), "columns": cols},
            success=True,
            latency_ms=exec_latency,
            extra_fields={"dataset_hit": f"views_{role}", "row_count": len(records)},
        )
        return res

        
    except Exception as e:
        err_msg = f"BigQuery execution error: {str(e)}"
        res = {
            "status": "error",
            "final_response": f"An error occurred while executing the query: {err_msg}",
            "error_message": err_msg,
        }
        DEFAULT_LOGGING_STORE.log_stage(
            session_id=session_id,
            role=role,
            turn_index=0,
            stage="execution",
            input_data=sql,
            output_data=err_msg,
            success=False,
            failure_reason=err_msg,
            latency_ms=(time.time() - start_time) * 1000,
        )
        return res
