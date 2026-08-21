from google.cloud import bigquery
import psycopg2
from psycopg2.extras import RealDictCursor
import yaml
import json
from pathlib import Path
from datetime import datetime
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, HTTPException, Depends, Header

import sys
from pathlib import Path
# Add root directory to Python path so we can import config.py
sys.path.append(str(Path(__file__).parent.parent))
from config import PROJECT_ID, METADATA_DATASET

YAML_PATH = Path("metadata/table_column_docs.yaml")
DOMAIN_YAML = Path("metadata/domain_tags.yaml")
RELATIONSHIP_YAML = Path("metadata/entity_relationships_corrected.yaml")

app = FastAPI(title="Dual Dashboard API (Admin & DB Manager)")

# --- PostgreSQL Credentials ---
DB_HOST = "localhost"
DB_NAME = "postgres"
DB_USER = "postgres"
DB_PASS = "123"

# --- Models ---
class UserLogin(BaseModel):
    username: str
    password: str

class BugReport(BaseModel):
    description: str

class SchemaApproval(BaseModel):
    updated_description: str
    questions: List[str] = []

class RoleAssignment(BaseModel):
    employee_id: str
    new_role: str

# --- Database Setup ---
def get_db():
    """Connects to PostgreSQL"""
    conn = psycopg2.connect(
        host=DB_HOST,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASS
    )
    # RealDictCursor makes rows behave like Python dictionaries
    return conn, conn.cursor(cursor_factory=RealDictCursor)

def init_db():
    conn, cursor = get_db()
    
    # Users table
    cursor.execute('''CREATE TABLE IF NOT EXISTS dashboard_users (
        id SERIAL PRIMARY KEY, username TEXT UNIQUE, password TEXT, role TEXT
    )''')
    
    # Bugs table
    cursor.execute('''CREATE TABLE IF NOT EXISTS system_bugs (
        id SERIAL PRIMARY KEY, reported_by TEXT, description TEXT, status TEXT DEFAULT 'OPEN', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # Schema Change Requests table
    cursor.execute('''CREATE TABLE IF NOT EXISTS schema_change_requests (
        id SERIAL PRIMARY KEY, 
        table_name TEXT, 
        column_name TEXT, 
        data_type TEXT, 
        description TEXT, 
        status TEXT DEFAULT 'PENDING_REVIEW', 
        approved_by TEXT, 
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # Insert default users if none exist
    cursor.execute("INSERT INTO dashboard_users (username, password, role) VALUES ('tech_admin', 'admin123', 'admin') ON CONFLICT DO NOTHING")
    cursor.execute("INSERT INTO dashboard_users (username, password, role) VALUES ('db_manager', 'db123', 'db_manager') ON CONFLICT DO NOTHING")
    
    conn.commit()
    conn.close()

# Try to init db on startup, ignore if DB isn't running yet
try:
    init_db()
except Exception as e:
    print(f"Warning: Could not initialize PostgreSQL. Is it running? {e}")

# --- Authentication Mock ---
def verify_admin(x_user_role: str = Header(...)):
    if x_user_role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return x_user_role

def verify_db_manager(x_user_role: str = Header(...)):
    if x_user_role != "db_manager":
        raise HTTPException(status_code=403, detail="DB Manager access required")
    return x_user_role

# ==========================================
#  LOGIN ENDPOINT
# ==========================================

@app.post("/api/login")
def login(credentials: UserLogin):
    """Your Frontend Login Page calls this endpoint."""
    conn, cursor = get_db()
    cursor.execute(
        "SELECT role FROM dashboard_users WHERE username = %s AND password = %s", 
        (credentials.username, credentials.password)
    )
    user = cursor.fetchone()
    conn.close()
    
    if not user:
        raise HTTPException(status_code=401, detail="Invalid username or password")
        
    return {
        "status": "SUCCESS",
        "username": credentials.username,
        "role": user["role"]
    }

# ==========================================
#  DATABASE MANAGER (NON-TECH) ENDPOINTS
# ==========================================

@app.get("/api/db_manager/docs/schema", dependencies=[Depends(verify_db_manager)])
def get_schema_docs():
    """Fetch existing table & column descriptions from YAML"""
    if not YAML_PATH.exists():
        return {"tables": []}
    with open(YAML_PATH, "r") as f:
        return yaml.safe_load(f)

@app.get("/api/db_manager/docs/domain", dependencies=[Depends(verify_db_manager)])
def get_domain_docs():
    """Fetch domain tags and summaries"""
    tags = {}
    if DOMAIN_YAML.exists():
        with open(DOMAIN_YAML, "r") as f:
            tags = yaml.safe_load(f)
            
    summary_path = Path("metadata/domain_summaries.md")
    summary = ""
    if summary_path.exists():
        with open(summary_path, "r") as f:
            summary = f.read()
            
    return {"tags": tags, "summaries": summary}


@app.get("/api/db_manager/schema/pending", dependencies=[Depends(verify_db_manager)])
def get_pending_schemas():
    conn, cursor = get_db()
    cursor.execute("SELECT * FROM schema_change_requests WHERE status = 'PENDING_REVIEW'")
    rows = cursor.fetchall()
    conn.close()
    return rows

def update_augment_script(table_name: str, column_name: str, questions: List[str]):
    import re
    path = Path("augment_with_dict.py")
    if not path.exists(): return
    content = path.read_text()
    chunk_id = f"{table_name}.col.{column_name}"
    q_str = " ".join(questions)
    new_entry = f'    "{chunk_id}": "{q_str}",\n'
    
    if f'"{chunk_id}":' in content:
        content = re.sub(rf'"{chunk_id}":\s*".*?",', f'"{chunk_id}": "{q_str}",', content)
    else:
        content = content.replace("DOMAIN_MAPPING = {", f"DOMAIN_MAPPING = {{\n{new_entry}")
    path.write_text(content)

def sync_bq_table_chunks(table_name: str, column_name: str, description: str, questions: List[str]):
    try:
        import uuid
        client = bigquery.Client(project=PROJECT_ID)
        chunk_id = f"{table_name}.col.{column_name}"
        q_str = " ".join(questions)
        new_chunk_text = f"Questions: {q_str} --- {description}"
        
        stg_table_id = f"{PROJECT_ID}.{METADATA_DATASET}.chunks_stg_{uuid.uuid4().hex[:6]}"
        schema = [
            bigquery.SchemaField("chunk_id", "STRING"),
            bigquery.SchemaField("chunk_text", "STRING")
        ]
        job_config = bigquery.LoadJobConfig(schema=schema)
        client.load_table_from_json([{"chunk_id": chunk_id, "chunk_text": new_chunk_text}], stg_table_id, job_config=job_config).result()
        
        sql = f"""
            UPDATE `{PROJECT_ID}.{METADATA_DATASET}.table_chunks` main
            SET chunk_text = stg.chunk_text
            FROM `{stg_table_id}` stg
            WHERE ENDS_WITH(main.chunk_id, stg.chunk_id)
        """
        client.query(sql).result()
        client.delete_table(stg_table_id)
    except Exception as e:
        print(f"Warning: Failed to sync BQ table_chunks: {e}")

def sync_bq_column_docs(table_name: str, column_name: str, description: str, data_type: str = "STRING"):
    """Syncs the column description and regenerates its embedding in BigQuery."""
    try:
        client = bigquery.Client(project=PROJECT_ID)
        model_id = f"{PROJECT_ID}.{METADATA_DATASET}.text_embedding_model"
        table_id = f"{PROJECT_ID}.{METADATA_DATASET}.column_docs"
        
        sql = f"""
        MERGE `{table_id}` T
        USING (
          SELECT 
            @table_name AS table_name, 
            @column_name AS column_name, 
            @description AS description, 
            @data_type AS data_type,
            (SELECT ml_generate_embedding_result FROM ML.GENERATE_EMBEDDING(
                MODEL `{model_id}`,
                (SELECT @description AS content)
            )) AS embedding
        ) S
        ON T.table_name = S.table_name AND T.column_name = S.column_name
        WHEN MATCHED THEN
          UPDATE SET description = S.description, embedding = S.embedding, data_type = S.data_type
        WHEN NOT MATCHED THEN
          INSERT (table_name, column_name, description, data_type, embedding)
          VALUES (S.table_name, S.column_name, S.description, S.data_type, S.embedding)
        """
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("table_name", "STRING", table_name),
                bigquery.ScalarQueryParameter("column_name", "STRING", column_name),
                bigquery.ScalarQueryParameter("description", "STRING", description),
                bigquery.ScalarQueryParameter("data_type", "STRING", data_type),
            ]
        )
        client.query(sql, job_config=job_config).result()
    except Exception as e:
        print(f"Warning: BigQuery Sync Failed for {table_name}.{column_name}: {e}")

@app.post("/api/db_manager/schema/approve/{request_id}", dependencies=[Depends(verify_db_manager)])
def approve_schema(request_id: int, approval: SchemaApproval, x_username: str = Header("db_manager")):
    conn, cursor = get_db()
    cursor.execute("SELECT * FROM schema_change_requests WHERE id = %s", (request_id,))
    req = cursor.fetchone()
    
    if not req or req["status"] != "PENDING_REVIEW":
        conn.close()
        raise HTTPException(status_code=400, detail="Invalid request")
    
    # 1. Update YAML File
    if YAML_PATH.exists():
        with open(YAML_PATH, "r") as f:
            yaml_data = yaml.safe_load(f) or {"tables": []}
    else:
        yaml_data = {"tables": []}

    table_name = req["table_name"]
    column_name = req["column_name"]
    updated_desc = approval.updated_description

    table_found = False
    for t in yaml_data.get("tables", []):
        if t.get("table") == table_name:
            if "columns" not in t or t["columns"] is None:
                t["columns"] = []
            
            col_found = False
            for col in t["columns"]:
                if col.get("column") == column_name:
                    col["description"] = updated_desc
                    col_found = True
                    break
            
            if not col_found:
                t["columns"].append({
                    "column": column_name,
                    "description": updated_desc
                })
            
            table_found = True
            break
            
    if not table_found:
        if "tables" not in yaml_data:
            yaml_data["tables"] = []
        yaml_data["tables"].append({
            "dataset": "unknown",
            "system_name": "New System",
            "table": table_name,
            "table_description": "Auto-added table",
            "columns": [{
                "column": column_name,
                "description": updated_desc
            }]
        })

    with open(YAML_PATH, "w") as f:
        yaml.dump(yaml_data, f, sort_keys=False)

    # 2. Update PostgreSQL
    cursor.execute("UPDATE schema_change_requests SET status='APPROVED', description=%s, approved_by=%s WHERE id=%s", 
                 (updated_desc, x_username, request_id))
    conn.commit()
    conn.close()
    
    # 3. Sync to BigQuery (Insert embedding)
    sync_bq_column_docs(table_name, column_name, updated_desc, req.get("data_type", "STRING"))
    
    # 4. Programmatically edit augment_with_dict.py
    if approval.questions:
        update_augment_script(table_name, column_name, approval.questions)
        # 5. Sync the text to BigQuery table_chunks
        sync_bq_table_chunks(table_name, column_name, updated_desc, approval.questions)
    
    return {"status": "SUCCESS"}

class EditSchemaRequest(BaseModel):
    table_name: str
    column_name: str
    updated_description: str
    questions: List[str] = []

class DomainMappingRequest(BaseModel):
    table_name: str
    dataset_name: str
    domains: List[str]

@app.post("/api/db_manager/schema/domains", dependencies=[Depends(verify_db_manager)])
def assign_domains(req: DomainMappingRequest):
    """Updates domain_tags.yaml and domain_summaries.yaml, then attempts to sync to BQ."""
    # 1. Update domain_tags.yaml
    if DOMAIN_YAML.exists():
        with open(DOMAIN_YAML, "r") as f:
            domain_tags_data = yaml.safe_load(f) or {"tables": []}
        
        table_found = False
        for t in domain_tags_data.get("tables", []):
            if t.get("table") == req.table_name:
                t["domain_tags"] = req.domains
                t["dataset"] = req.dataset_name
                table_found = True
                break
        
        if not table_found:
            domain_tags_data["tables"].append({
                "dataset": req.dataset_name,
                "system_name": "Unknown System",
                "table": req.table_name,
                "domain_tags": req.domains,
                "table_description": "Auto-added via domain mapping"
            })
            
        with open(DOMAIN_YAML, "w") as f:
            yaml.dump(domain_tags_data, f, sort_keys=False)

    # 2. Update domain_summaries.yaml
    summary_yaml_path = Path("metadata/domain_summaries.yaml")
    if summary_yaml_path.exists():
        with open(summary_yaml_path, "r") as f:
            summary_data = yaml.safe_load(f)
            
        try:
            domain_sections = summary_data["content"][0]["subsections"][0]["subsections"]
            for sec in domain_sections:
                domain_name = sec["heading"].replace("`", "").strip()
                if domain_name in req.domains:
                    if "**Tables:**" in sec["body"]:
                        if req.table_name not in sec["body"]:
                            sec["body"] += f", {req.table_name}"
            
            with open(summary_yaml_path, "w") as f:
                yaml.dump(summary_data, f, sort_keys=False)
        except Exception as e:
            print(f"Warning: Failed to parse/update domain_summaries.yaml: {e}")

    # 3. BigQuery Sync (Best Effort)
    try:
        client = bigquery.Client(project=PROJECT_ID)
        
        # We will attempt to update the rag_meta tables dynamically based on standard formats
        print(f"Domain Sync: Syncing {req.table_name} to BigQuery is requested.")
        
    except Exception as e:
        print(f"BQ sync failed: {e}")

    return {"status": "SUCCESS"}

@app.post("/api/db_manager/schema/edit", dependencies=[Depends(verify_db_manager)])
def edit_existing_schema(req: EditSchemaRequest, x_username: str = Header("db_manager")):
    """Edits an existing column in the YAML and syncs to BigQuery."""
    if not YAML_PATH.exists():
        raise HTTPException(status_code=400, detail="YAML file not found")
        
    with open(YAML_PATH, "r") as f:
        yaml_data = yaml.safe_load(f) or {"tables": []}
        
    updated = False
    for t in yaml_data.get("tables", []):
        if t.get("table") == req.table_name:
            for col in t.get("columns", []):
                if col.get("column") == req.column_name:
                    col["description"] = req.updated_description
                    updated = True
                    break
            break
            
    if not updated:
        raise HTTPException(status_code=404, detail="Table or column not found in YAML")
        
    with open(YAML_PATH, "w") as f:
        yaml.dump(yaml_data, f, sort_keys=False)
        
    # Sync to BigQuery (Update embedding)
    sync_bq_column_docs(req.table_name, req.column_name, req.updated_description)
    
    # Update questions programmatically and sync chunks
    if req.questions:
        update_augment_script(req.table_name, req.column_name, req.questions)
        sync_bq_table_chunks(req.table_name, req.column_name, req.updated_description, req.questions)
    
    return {"status": "SUCCESS"}

@app.get("/api/db_manager/er_graph", dependencies=[Depends(verify_db_manager)])
def get_er_graph():
    if not RELATIONSHIP_YAML.exists():
        return {"nodes": [], "edges": []}
    with open(RELATIONSHIP_YAML, "r") as f:
        data = yaml.safe_load(f)
    edges = [{"source": j["from_table"], "target": j["to_table"], "label": j["relationship_type"]} for j in data.get("relationships", [])]
    nodes = list(set([e["source"] for e in edges] + [e["target"] for e in edges]))
    return {"nodes": [{"id": n, "label": n} for n in nodes], "edges": edges}

@app.get("/api/db_manager/roles/available", dependencies=[Depends(verify_db_manager)])
def get_available_roles():
    """Dynamically fetches roles by looking at the 'views_*' datasets in BigQuery."""
    try:
        # This uses your existing Google credentials
        client = bigquery.Client(project=PROJECT_ID)
        
        # Ask BigQuery for a list of all datasets in the project
        datasets = list(client.list_datasets())
        
        live_roles = []
        for d in datasets:
            if d.dataset_id.startswith("views_"):
                # Strip the "views_" prefix so "views_loan_officer" becomes "loan_officer"
                role_name = d.dataset_id.replace("views_", "")
                live_roles.append(role_name)
                
        # Fallback just in case the warehouse is empty
        if not live_roles:
            live_roles = ["no_views_found_in_bq"]
            
        return {"roles": live_roles}
        
    except Exception as e:
        print(f"BigQuery Fetch Error: {e}")
        return {"roles": ["bq_connection_error"]}

@app.post("/api/db_manager/roles/assign", dependencies=[Depends(verify_db_manager)])
def assign_employee_role(assignment: RoleAssignment):
    try:
        client = bigquery.Client(project=PROJECT_ID)
        
        query = f"""
            UPDATE `{PROJECT_ID}.base.employees`
            SET role = @new_role
            WHERE employee_id = @emp_id
        """
        
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("new_role", "STRING", assignment.new_role),
                bigquery.ScalarQueryParameter("emp_id", "STRING", assignment.employee_id)
            ]
        )
        
        query_job = client.query(query, job_config=job_config)
        query_job.result() 
        
        if query_job.num_dml_affected_rows and query_job.num_dml_affected_rows > 0:
            return {"message": f"Successfully promoted employee {assignment.employee_id} to {assignment.new_role} in BigQuery."}
        else:
            raise HTTPException(status_code=404, detail=f"Employee {assignment.employee_id} not found in BigQuery.")
            
    except Exception as e:
        print(f"Role Update Error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update role in BigQuery: {str(e)}")

@app.post("/api/db_manager/bugs", dependencies=[Depends(verify_db_manager)])
def report_bug(bug: BugReport, x_username: str = Header("db_manager")):
    conn, cursor = get_db()
    cursor.execute("INSERT INTO system_bugs (reported_by, description) VALUES (%s, %s)", (x_username, bug.description))
    conn.commit()
    conn.close()
    return {"message": "Bug reported to Admin successfully."}

# ==========================================
#  TECH ADMIN ENDPOINTS
# ==========================================

@app.get("/api/admin/logs", dependencies=[Depends(verify_admin)])
def get_session_logs(limit: int = 50):
    return {"logs": ["Simulated Session Log 1: Used 500 tokens", "Simulated Session Log 2: Used 1200 tokens"]}

@app.get("/api/admin/prompts", dependencies=[Depends(verify_admin)])
def get_system_prompts():
    return {
        "sql_generation_prompt": "You are a BigQuery expert...",
        "guardrail_prompt": "Ensure no destructive DDL..."
    }

@app.post("/api/admin/bugs/{bug_id}/resolve", dependencies=[Depends(verify_admin)])
def resolve_bug(bug_id: int):
    conn, cursor = get_db()
    cursor.execute("UPDATE system_bugs SET status='RESOLVED' WHERE id=%s", (bug_id,))
    conn.commit()
    conn.close()
    return {"message": "Bug resolved."}

@app.post("/api/admin/config/model", dependencies=[Depends(verify_admin)])
def update_llm_model(model_name: str):
    return {"message": f"Successfully updated active model to {model_name}"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
