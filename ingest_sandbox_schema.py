import os
import yaml
import psycopg2
from pathlib import Path
from google.cloud import bigquery

# --- Configuration ---
BQ_PROJECT = "project-f118f2cb-f557-4d4f-990"

# PostgreSQL Credentials (must match your dual_dashboard_api.py)
DB_HOST = "localhost"
DB_NAME = "postgres"
DB_USER = "postgres"
DB_PASS = "123"

YAML_PATH = Path("metadata/table_column_docs.yaml")

def get_pg_connection():
    return psycopg2.connect(
        host=DB_HOST,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASS
    )

def load_yaml_baseline():
    """Loads the current source of truth from YAML."""
    if not YAML_PATH.exists():
        return {}
    with open(YAML_PATH, "r") as f:
        data = yaml.safe_load(f) or {"tables": []}
        
    # Build a quick lookup set: {"table_name.column_name"}
    known_columns = set()
    for table in data.get("tables", []):
        t_name = table.get("table")
        for col in table.get("columns", []):
            known_columns.add(f"{t_name}.{col.get('column')}")
            
    return known_columns

def fetch_bigquery_schema():
    """Fetches the live schema from all BigQuery datasets dynamically."""
    client = bigquery.Client(project=BQ_PROJECT)
    all_columns = []
    
    # Load external ignore configuration (Strategy 2)
    ignore_config_path = Path("metadata/dataset_ignore_list.yaml")
    ignore_exact = []
    ignore_prefixes = []
    if ignore_config_path.exists():
        with open(ignore_config_path, "r") as f:
            config = yaml.safe_load(f) or {}
            ignore_exact = config.get("ignore_exact_matches", [])
            ignore_prefixes = config.get("ignore_prefixes", [])
    
    # Dynamically fetch all datasets in the project
    print(" Fetching list of all datasets from BigQuery...")
    datasets = [d.dataset_id for d in client.list_datasets()]
    
    for dataset in datasets:
        # Apply the external ignore rules
        if dataset in ignore_exact:
            continue
        if any(dataset.startswith(prefix) for prefix in ignore_prefixes):
            continue
        query = f"""
            SELECT table_name, column_name, data_type 
            FROM `{BQ_PROJECT}.{dataset}.INFORMATION_SCHEMA.COLUMNS`
        """
        print(f" Scanning BigQuery dataset: {dataset}...")
        try:
            results = client.query(query).result()
            for row in results:
                all_columns.append({
                    "dataset": dataset,
                    "table_name": row.table_name, 
                    "column_name": row.column_name, 
                    "data_type": row.data_type
                })
        except Exception as e:
            print(f" Error querying {dataset}: {e}")
            
    return all_columns

def run_diff_engine():
    """Compares BQ against YAML and pushes new columns to Postgres."""
    known_columns = load_yaml_baseline()
    live_columns = fetch_bigquery_schema()
    
    if not live_columns:
        print(" No columns found in BigQuery (or connection failed). Exiting.")
        return
        
    conn = get_pg_connection()
    cursor = conn.cursor()
    
    # Ensure the table exists before we try to insert into it
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
    conn.commit()
    
    new_columns_found = 0
    stale_columns_cleared = 0
    for col in live_columns:
        lookup_key = f"{col['table_name']}.{col['column_name']}"
        
        # 1. Is this column already documented in the YAML?
        if lookup_key not in known_columns:
            
            # 2. Is this column already pending review in Postgres?
            cursor.execute(
                "SELECT id FROM schema_change_requests WHERE table_name = %s AND column_name = %s",
                (col['table_name'], col['column_name'])
            )
            existing_request = cursor.fetchone()
            
            if not existing_request:
                # 3. We found a brand new column! Push it to Postgres for the Database Manager.
                print(f" NEW DIFF FOUND: {col['dataset']}.{lookup_key} ({col['data_type']})")
                
                cursor.execute("""
                    INSERT INTO schema_change_requests 
                    (table_name, column_name, data_type, description, status) 
                    VALUES (%s, %s, %s, %s, 'PENDING_REVIEW')
                """, (col['table_name'], col['column_name'], col['data_type'], f"Requires DB Manager description (Found in {col['dataset']})"))
                
                new_columns_found += 1
                
    # Global Cleanup Pass: Remove stale requests from Postgres
    cursor.execute("SELECT id, table_name, column_name FROM schema_change_requests WHERE status = 'PENDING_REVIEW'")
    pending_requests = cursor.fetchall()
    
    for req in pending_requests:
        req_id = req[0]
        t_name = req[1]
        c_name = req[2]
        lookup_key = f"{t_name}.{c_name}"
        
        # A pending request is stale if:
        # 1. The column was deleted from BigQuery (doesn't exist in live_columns)
        # 2. OR The column was added to the YAML (exists in known_columns)
        exists_in_bq = any(c['table_name'] == t_name and c['column_name'] == c_name for c in live_columns)
        documented_in_yaml = (lookup_key in known_columns)
        
        if not exists_in_bq or documented_in_yaml:
            cursor.execute("DELETE FROM schema_change_requests WHERE id = %s", (req_id,))
            stale_columns_cleared += 1
                
    conn.commit()
    conn.close()
    
    if stale_columns_cleared > 0:
        print(f" Automatically cleared {stale_columns_cleared} stale pending schemas from Postgres (they were either deleted from BQ or are now in the YAML).")
        
    if new_columns_found > 0:
        print(f" Successfully pushed {new_columns_found} new columns to the Database Manager Dashboard!")
    else:
        print(" Scan complete. No new columns found in BigQuery.")
if __name__ == "__main__":
    print(" Starting Schema Ingestion Engine for 10 Datasets...")
    run_diff_engine()
