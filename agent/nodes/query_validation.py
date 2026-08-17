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

import yaml
from pathlib import Path

def load_disconnected_edges() -> set:
    yaml_path = Path(__file__).resolve().parent.parent.parent / "metadata" / "entity_relationships_corrected.yaml"
    try:
        with open(yaml_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            edges = set()
            for rel in data.get("relationships", []):
                if rel.get("data_matched") is False:
                    f_table = rel.get("from_table", "").lower()
                    t_table = rel.get("to_table", "").lower()
                    edges.add((f_table, t_table))
                    edges.add((t_table, f_table))
            return edges
    except Exception:
        return set()

DISCONNECTED_EDGES = load_disconnected_edges()


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

    # Rule 4b: Relational Entity Misassignment Guardrail (Pre-flight AST Check)
    FORBIDDEN_ENTITY_COLUMNS = {
        "compliance_flags": "compliance_flags is a standalone table (views_{role}.compliance_flags), NOT a column on loans or customers. Join views_{role}.compliance_flags cf ON l.loan_id = cf.loan_id.",
        "credit_score": "credit_score is on views_{role}.customer_risk_scores, NOT customers or loans. Join views_{role}.customer_risk_scores crs ON c.customer_id = crs.customer_id.",
        "risk_category": "risk_category is on views_{role}.customer_risk_scores, NOT customers or loans. Join views_{role}.customer_risk_scores crs ON c.customer_id = crs.customer_id.",
        "kyc_documents": "kyc_documents is a standalone table (views_{role}.kyc_documents), NOT a column on customers. Join views_{role}.kyc_documents kd ON c.customer_id = kd.customer_id.",
        "claims": "insurance_claims is a standalone table (views_{role}.insurance_claims), NOT a column on insurance_policies. Join views_{role}.insurance_claims ic ON ip.policy_id = ic.policy_id.",
        "designation": "designation is on views_{role}.zoho_employee_records (z.designation), NOT employees e. Select e.role on employees or join views_{role}.zoho_employee_records z ON e.employee_id = z.employee_id.",
    }
    
    for column in ast.find_all(exp.Column):
        col_name = column.name.lower()
        if col_name in FORBIDDEN_ENTITY_COLUMNS:
            table_alias = column.table
            if table_alias and table_alias.lower() in ("l", "c", "e", "loans", "customers", "employees", "ip", "insurance_policies"):
                err_detail = FORBIDDEN_ENTITY_COLUMNS[col_name].format(role=role)
                return False, {
                    "rule_violated": "Rule 4b: Relational Entity Misassignment",
                    "detail": err_detail,
                    "offending_sql_fragment": f"{table_alias}.{col_name}",
                }, 0

    # Rule 4c: 100% Dynamic Metadata Disconnected Edge AST Interception
    # Dynamically maps table aliases to table names and checks DISCONNECTED_EDGES loaded from YAML metadata
    alias_map = {}
    for table_expr in ast.find_all(exp.Table):
        t_name = table_expr.name.lower()
        t_alias = table_expr.alias.lower() if table_expr.alias else t_name
        alias_map[t_alias] = t_name

    for eq in ast.find_all(exp.EQ):
        left_col = eq.this
        right_col = eq.expression
        if isinstance(left_col, exp.Column) and isinstance(right_col, exp.Column):
            table_a = alias_map.get(left_col.table.lower(), left_col.table.lower())
            table_b = alias_map.get(right_col.table.lower(), right_col.table.lower())
            if (table_a, table_b) in DISCONNECTED_EDGES or (table_b, table_a) in DISCONNECTED_EDGES:
                fallback_target = "loan_applications" if "loans" in (table_a, table_b) else "connected_entity"
                return False, {
                    "rule_violated": "Rule 4c: Disconnected Metadata Edge Intercepted",
                    "detail": f"Do NOT join views_{role}.{table_a} directly to views_{role}.{table_b} on {left_col.this.name} (this relationship is tagged data_matched: false in metadata and yields 0 matched rows). Join views_{role}.{fallback_target} instead.",
                    "offending_sql_fragment": eq.sql(),
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
