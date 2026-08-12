"""
agent/nodes/sql_generation.py — Node [4]: LLM SQL Generator Agent.
Generates BigQuery SQL targeting views_<role>.* views. Biases toward aggregation
when output_mode='summary'. Incorporates structured error feedback on retries.
"""

import time
from typing import Dict, Any
from langchain_core.messages import SystemMessage, HumanMessage

from agent.state import GraphState
from agent.groq_client import invoke_groq_with_retry
from agent.logging_store import DEFAULT_LOGGING_STORE

SQL_GEN_SYSTEM_PROMPT = """You are an expert BigQuery SQL generator for an NBFC data warehouse.
Your job is to produce a single, valid, highly accurate Google BigQuery SQL query to answer the user's analytical question.

CRITICAL CONSTRAINTS:
1. Target ONLY tables in the provided view dataset (`views_{role}.*`). NEVER query base/raw datasets (e.g. `base`, `lms`, `crm`, `los`).
2. Generate EXACTLY ONE `SELECT` or `WITH` statement. No DDL/DML (no `INSERT`, `UPDATE`, `DELETE`, `DROP`, `CREATE`, `ALTER`).
3. DO NOT USE `SELECT *`. You MUST explicitly enumerate the required columns (e.g. `SELECT employee_id, name, branch_id`).
4. Output MODE BIAS:
   - If Output Mode is "summary": Bias toward aggregations (`COUNT`, `SUM`, `AVG`), `GROUP BY`, and top metrics rather than raw row lists.
   - If Output Mode is "exact": Select individual fields suitable for tabular display.
5. Use literal enum strings provided in the schema context (e.g. `'npa'`, `'approved'`, `'Jaipur Branch'`) matching exact case.
6. Output ONLY the executable SQL query inside ```sql ... ``` code block. No markdown conversation text.
7. Use ONLY column names that explicitly appear in the provided Schema Context. NEVER invent or assume column names (e.g. use `c.name` for customer name, NOT `c.customer_name`; do NOT use `interest_amount` or `principal_amount` unless explicitly in Schema Context; use `disbursed_amount` and `interest_rate`).

8. In BigQuery SQL, access array elements using `[OFFSET(0)]` or `[ORDINAL(1)]`. NEVER put a dot before brackets (e.g. write `arr[OFFSET(0)]`, NOT `arr.[OFFSET(0)]` or `.element[0]`).
9. Column ownership: `min_amount` and `max_amount` belong to `loan_products p` (NOT `loans l`). On `loans l`, available columns are `disbursed_amount`, `interest_rate`, `tenure_months`, `disbursement_date`, `status`. NEVER reference `min_amount` or `max_amount` on `loans l`.
10. When referencing columns in JOIN queries, ALWAYS qualify columns with the correct table alias (e.g. `l.disbursed_amount` for `loans l`, `b.branch_name` for `branches b`).
11. Strictly follow Foreign Key relationship paths in Schema Context when joining tables (e.g. `customers c` joins to `loans l` on `c.customer_id = l.customer_id`, NOT `c.branch_id`).
"""









RETRY_PROMPT_TEMPLATE = """Previous SQL generation attempt failed validation:

OFFENDING SQL:
{offending_sql}

VALIDATION ERROR OBJECT:
- Rule Violated: {rule_violated}
- Error Detail: {detail}
- Fragment: {offending_fragment}

CRITICAL FIX INSTRUCTIONS:
- If error mentions "Name X not found inside Y" (e.g. "disbursed_amount not found inside b", "loan_tenure not found inside l", or "branch_id not found inside c"):
  1. Verify which table column X actually belongs to (e.g. `l.disbursed_amount` for `loans l`, `l.branch_id` for `loans l` — `customers c` does NOT have `branch_id`, join `branches b` on `l.branch_id = b.branch_id`).
  2. Verify the exact column name in Schema Context (e.g. use `tenure_months` for tenure, `income_band` / `occupation` on `customers`).
- Ensure `SUM(l.disbursed_amount)` is used directly without unnecessary string splitting or casting on numeric columns.



Please fix the error, strictly follow all schema constraints and rules, and generate a revised BigQuery SQL query.
"""



def sql_generation_node(state: GraphState) -> Dict[str, Any]:
    """LangGraph node generating BigQuery SQL from schema and question."""
    start_time = time.time()
    session_id = state.get("session_id", "default")
    role = state.get("role", "unknown")
    question = state.get("question", "")
    output_mode = state.get("output_mode", "exact")
    schema_context = state.get("schema_context", "")
    attempts = state.get("validation_attempts", 0)
    prev_error = state.get("validation_error_object")
    prev_sql = state.get("sql_query")
    propagated_filters = state.get("propagated_filters", [])
    
    system_prompt = SQL_GEN_SYSTEM_PROMPT.format(role=role)
    
    prompt_content = [
        f"USER ROLE: {role}",
        f"OUTPUT MODE: {output_mode}",
        f"USER QUESTION: {question}",
        "",
        schema_context,
    ]

    # Inject explicit propagated join filter instructions if present
    if propagated_filters:
        filter_lines = ["REQUIRED JOIN CONDITIONS & TRAVERSED FILTERS:"]
        for pf in propagated_filters:
            f_tbl = pf.get("from_table", "")
            f_col = pf.get("from_column", "")
            t_tbl = pf.get("to_table", "")
            t_col = pf.get("to_column", "")
            flt = pf.get("filter", "")
            filter_lines.append(f" - When joining `{f_tbl}` to `{t_tbl}`, enforce: `{f_tbl}.{f_col} = {t_tbl}.{t_col}`" + (f" (filter condition: {flt})" if flt else ""))
        prompt_content.append("\n".join(filter_lines))

    
    # If this is a retry attempt, append previous error feedback
    if prev_error and prev_sql:
        retry_msg = RETRY_PROMPT_TEMPLATE.format(
            offending_sql=prev_sql,
            rule_violated=prev_error.get("rule_violated", "Unknown"),
            detail=prev_error.get("detail", "Validation failed"),
            offending_fragment=prev_error.get("offending_sql_fragment", "N/A"),
        )
        prompt_content.append(retry_msg)
        
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content="\n\n".join(prompt_content)),
    ]
    
    try:
        response = invoke_groq_with_retry(messages, temperature=0.1)
        meta = getattr(response, "response_metadata", {}) or {}
        llm_model = meta.get("model_name")
        tokens_used = meta.get("token_usage")
        raw_text = response.content.strip()
        
        # Extract SQL from code block
        if "```sql" in raw_text:
            sql = raw_text.split("```sql")[1].split("```")[0].strip()
        elif "```" in raw_text:
            sql = raw_text.split("```")[1].split("```")[0].strip()
        else:
            sql = raw_text.strip()
            
        # Clean trailing semicolons
        sql = sql.rstrip(";")
        
        res = {
            "sql_query": sql,
            "validation_attempts": attempts + 1,
        }
        
        DEFAULT_LOGGING_STORE.log_stage(
            session_id=session_id,
            role=role,
            turn_index=0,
            stage="sql_generation",
            input_data={"question": question, "attempt": attempts + 1},
            output_data=sql,
            success=True,
            latency_ms=(time.time() - start_time) * 1000,
            llm_model=llm_model,
            tokens_used=tokens_used,
        )
        return res

        
    except Exception as e:
        err_msg = f"SQL Generation error: {str(e)}"
        res = {
            "status": "error",
            "final_response": "An error occurred while building the SQL query.",
            "error_message": err_msg,
        }
        DEFAULT_LOGGING_STORE.log_stage(
            session_id=session_id,
            role=role,
            turn_index=0,
            stage="sql_generation",
            input_data=question,
            output_data=err_msg,
            success=False,
            failure_reason=err_msg,
            latency_ms=(time.time() - start_time) * 1000,
        )
        return res
