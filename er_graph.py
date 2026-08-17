import yaml
from google.cloud import bigquery

PROJECT_ID = "project-f118f2cb-f557-4d4f-990"

def load_relationships(filepath: str) -> list[dict]:
    """Loads the ER relationships from a YAML file."""
    with open(filepath, 'r') as f:
        data = yaml.safe_load(f)
    return data.get("relationships", [])

def get_authorized_tables(client: bigquery.Client, role_dataset: str) -> set[str]:
    """Fetches the list of all table names available in the given dataset."""
    query = f"""
    SELECT table_name
    FROM `{PROJECT_ID}.{role_dataset}.INFORMATION_SCHEMA.TABLES`
    """
    try:
        rows = client.query(query).result()
        return {r.table_name for r in rows}
    except Exception as e:
        print(f"Warning: Could not fetch tables for dataset {role_dataset}: {e}")
        return set()

def expand_with_er(seed_tables: list[str], role_dataset: str, relationships: list[dict], client: bigquery.Client) -> list[str]:
    """
    Expands the seed tables by 1 hop using the ER relationships.
    Returns a list of fully qualified table names authorized for the user.
    """
    if not seed_tables:
        return []
        
    expanded_set = set(seed_tables)
    
    # Traverse 1 hop
    for rel in relationships:
        from_t = rel.get("from_table")
        to_t = rel.get("to_table")
        
        if from_t in seed_tables:
            expanded_set.add(to_t)
        if to_t in seed_tables:
            expanded_set.add(from_t)
            
    # Role filter: Ensure we only include tables the user actually has access to
    authorized_tables = get_authorized_tables(client, role_dataset)
    
    final_tables = []
    for t in expanded_set:
        if t in authorized_tables:
            final_tables.append(f"{role_dataset}.{t}")
            
    return final_tables
