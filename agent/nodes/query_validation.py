"""
agent/nodes/query_validation.py — Node [5]: Multi-rule Query Validation Agent.
Validates generated SQL using sqlglot AST parsing and BigQuery dry-run checks.
Returns structured failure payload on error for self-correction retries.
"""

import time
import sqlglot
import sqlglot.expressions as exp
from typing import Dict, Any, Tuple, Optional
from google.cloud import bigquery

from config_guardrails import MAX_BYTES_BILLED_CAP, MAX_ROW_COUNT_CAP, MAX_VALIDATION_RETRIES

from agent.state import GraphState
from agent.logging_store import DEFAULT_LOGGING_STORE
from bq_client import get_client_for_role


def validate_sql_query(
    sql: str,
    role: str,
    output_mode: str,
) -> Tuple[bool, Optional[Dict[str, Any]], Optional[int]]:
    """
    Executes full 6-rule validation chain in exact sequence.
    Returns (is_valid, error_payload_dict, total_bytes_processed).
    """
    target_dataset = f"views_{role}"
    
    # Rule 1: Syntax validity via sqlglot AST parse
    try:
        parsed_expressions = sqlglot.parse(sql, read="bigquery")
        if not parsed_expressions or parsed_expressions[0] is None:
            return False, {
                "rule_violated": "Rule 1: Syntax Error",
                "detail": "Failed to parse BigQuery SQL syntax.",
                "offending_sql_fragment": sql[:100],
            }, 0
        ast = parsed_expressions[0]
    except Exception as e:
        return False, {
            "rule_violated": "Rule 1: Syntax Error",
            "detail": f"SQL syntax error: {str(e)}",
            "offending_sql_fragment": sql[:100],
        }, 0

    # Rule 2: Read-only enforcement (SELECT or WITH only)
    if not isinstance(ast, (exp.Select, exp.Expression)):
        return False, {
            "rule_violated": "Rule 2: Read-Only Violation",
            "detail": "Only single SELECT or WITH queries are allowed. DDL/DML statements are prohibited.",
            "offending_sql_fragment": type(ast).__name__,
        }, 0
        
    # AST statement type check for non-select root
    sql_upper = sql.strip().upper()
    if not (sql_upper.startswith("SELECT") or sql_upper.startswith("WITH")):
        return False, {
            "rule_violated": "Rule 2: Read-Only Violation",
            "detail": "Query must start with SELECT or WITH.",
            "offending_sql_fragment": sql_upper[:30],
        }, 0

    # Rule 3: Prohibit bare SELECT *
    has_star = False
    for star in ast.find_all(exp.Star):
        has_star = True
        break
    if has_star:
        return False, {
            "rule_violated": "Rule 3: Bare SELECT * Prohibition",
            "detail": "Queries using SELECT * are prohibited. Explicitly enumerate required column names.",
            "offending_sql_fragment": "SELECT *",
        }, 0

    # Rule 4: Scoped to views_<role>.* dataset ONLY
    tables = [table.name for table in ast.find_all(exp.Table)]
    for table in ast.find_all(exp.Table):
        db_name = table.db
        if db_name and db_name.lower() != target_dataset.lower():
            return False, {
                "rule_violated": "Rule 4: Dataset Access Boundary",
                "detail": f"Access denied to dataset '{db_name}'. Queries MUST target `{target_dataset}.*` only.",
                "offending_sql_fragment": f"{db_name}.{table.name}",
            }, 0

    # Rule 5 & 6: BigQuery Dry Run (Byte-size cap & Syntax/Schema check)
    client = get_client_for_role(role)
    job_config = bigquery.QueryJobConfig(dry_run=True, use_query_cache=False)
    
    try:
        dry_run_job = client.query(sql, job_config=job_config)
        total_bytes = dry_run_job.total_bytes_processed
        
        if total_bytes > MAX_BYTES_BILLED_CAP:
            mb_scanned = total_bytes / (1024 * 1024)
            mb_cap = MAX_BYTES_BILLED_CAP / (1024 * 1024)
            return False, {
                "rule_violated": "Rule 5: Byte Scan Limit Exceeded",
                "detail": f"Query dry-run estimated {mb_scanned:.2f} MB scanned, exceeding maximum allowed limit of {mb_cap:.2f} MB.",
                "offending_sql_fragment": f"total_bytes_processed={total_bytes}",
            }, total_bytes
            
    except Exception as e:
        err_msg = str(e)
        return False, {
            "rule_violated": "Rule 5: BigQuery Dry-Run Execution Error",
            "detail": f"BigQuery dry-run error: {err_msg}",
            "offending_sql_fragment": sql[:100],
        }, 0

    return True, None, total_bytes


def query_validation_node(state: GraphState) -> Dict[str, Any]:
    """LangGraph node validating generated SQL against guardrail rules."""
    start_time = time.time()
    session_id = state.get("session_id", "default")
    role = state.get("role", "unknown")
    sql = state.get("sql_query", "")
    output_mode = state.get("output_mode", "exact")
    attempts = state.get("validation_attempts", 1)
    
    if not sql:
        err_obj = {
            "rule_violated": "Rule 0: Empty Query",
            "detail": "SQL query is empty.",
            "offending_sql_fragment": "",
        }
        res = {
            "is_sql_valid": False,
            "validation_error_object": err_obj,
        }
        return res
        
    is_valid, err_obj, bytes_processed = validate_sql_query(sql, role, output_mode)
    
    if is_valid:
        res = {
            "is_sql_valid": True,
            "validation_error_object": None,
            "bytes_processed": bytes_processed or 0,
        }
        DEFAULT_LOGGING_STORE.log_stage(
            session_id=session_id,
            role=role,
            turn_index=0,
            stage="validation",
            input_data={"sql": sql, "attempt": attempts},
            output_data="PASSED",
            success=True,
            latency_ms=(time.time() - start_time) * 1000,
            extra_fields={"bytes_processed": bytes_processed},
        )
        return res
    else:
        # Check retry limit
        exceeded_retries = attempts >= MAX_VALIDATION_RETRIES
        res = {
            "is_sql_valid": False,
            "validation_error_object": err_obj,
            "bytes_processed": bytes_processed or 0,
        }
        if exceeded_retries:
            res["status"] = "failed"
            res["final_response"] = (
                "I was unable to build a valid query for this question after multiple attempts. "
                "Please try rephrasing your question."
            )
            
        DEFAULT_LOGGING_STORE.log_stage(
            session_id=session_id,
            role=role,
            turn_index=0,
            stage="validation",
            input_data={"sql": sql, "attempt": attempts},
            output_data=err_obj,
            success=False,
            failure_reason=err_obj.get("detail"),
            latency_ms=(time.time() - start_time) * 1000,
            extra_fields={"exceeded_retries": exceeded_retries},
        )
        return res
