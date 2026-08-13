import os
import google.generativeai as genai
from google.cloud import bigquery

# Use environment variable for API key
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
PROJECT_ID = "project-f118f2cb-f557-4d4f-990"

def fetch_table_schemas(client: bigquery.Client, table_names: list[str]) -> str:
    """
    Fetches the schema for a list of fully qualified table names 
    (e.g., 'views_hr_officer.incentive_payouts') directly from BigQuery.
    """
    schemas = []
    
    for fully_qualified_table in table_names:
        parts = fully_qualified_table.split('.')
        if len(parts) == 2:
            dataset_id, table_id = parts
        elif len(parts) == 3:
            _, dataset_id, table_id = parts
        else:
            continue
            
        query = f"""
        SELECT column_name, data_type 
        FROM `{PROJECT_ID}.{dataset_id}.INFORMATION_SCHEMA.COLUMNS`
        WHERE table_name = @table_id
        """
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("table_id", "STRING", table_id)
            ]
        )
        try:
            rows = client.query(query, job_config=job_config).result()
            schema_lines = [f"Table: {fully_qualified_table}"]
            for r in rows:
                schema_lines.append(f"- {r.column_name} ({r.data_type})")
            schemas.append("\n".join(schema_lines))
        except Exception as e:
            print(f"Warning: Could not fetch schema for {fully_qualified_table}: {e}")
            
    return "\n\n".join(schemas)

def generate_sql(raw_question: str, filters: list[str], table_names: list[str]) -> str:
    """
    Generates a BigQuery SQL statement given the raw question, extracted filters, 
    and the top retrieved table schemas.
    """
    if not table_names:
        return "ERROR: No tables retrieved."

    client = bigquery.Client(project=PROJECT_ID)
    schemas_text = fetch_table_schemas(client, table_names)
    
    if not schemas_text:
        return "ERROR: Could not fetch schemas for the provided tables."

    model = genai.GenerativeModel("gemini-3.5-flash-lite")
    
    prompt = f"""
You are a highly skilled BigQuery SQL developer.
Your task is to write a valid, executable BigQuery Standard SQL query based on the user's question, applying the requested filters to the provided table schemas.

### User Question:
"{raw_question}"

### Extracted Filters:
{json.dumps(filters)}

### Available Table Schemas:
{schemas_text}

### Instructions:
1. Write a single, valid BigQuery `SELECT` statement.
2. Use ONLY the tables and columns provided in the schema above.
3. If the user mentions timeframes (e.g., "last month", "yesterday"), use BigQuery date/time functions (e.g., `CURRENT_DATE()`, `DATE_SUB()`, `DATE_TRUNC()`) to calculate the range dynamically. Do not hardcode literal dates unless absolutely necessary.
4. Ensure you use the exact fully qualified table names as provided (e.g., `views_hr_officer.incentive_payouts`).
5. Always use LOWER() for string equality comparisons in the WHERE clause (e.g., `LOWER(status) = 'active'`) to prevent case-sensitivity mismatches.
6. Output ONLY the raw SQL query. Do not wrap it in ```sql ... ``` markdown blocks, do not explain the query. Just return the pure SQL.
"""

    response = model.generate_content(
        prompt,
        generation_config={"temperature": 0.0}
    )
    
    # Strip markdown if the LLM ignores the instruction
    sql = response.text.strip()
    if sql.startswith("```sql"):
        sql = sql[6:]
    if sql.startswith("```"):
        sql = sql[3:]
    if sql.endswith("```"):
        sql = sql[:-3]
        
    return sql.strip()
