"""
agent/nodes/retrieval.py — Node [3]: Deterministic Retrieval & Multi-Hop Expansion.
Filters candidate tables by matched domains, expands candidate set via graph BFS
over entity_relationships_corrected.yaml, and assembles schema documentation context.
"""

import time
import yaml
from pathlib import Path
from typing import Dict, Any, List, Set
from collections import deque

from config import METADATA_DIR
from agent.state import GraphState
from agent.logging_store import DEFAULT_LOGGING_STORE

try:
    from retrieval import retrieve_relevant_tables
except ImportError:
    retrieve_relevant_tables = None


def load_domain_tags() -> List[Dict[str, Any]]:
    """Load domain_tags.yaml mapping tables to domains."""
    path = METADATA_DIR / "domain_tags.yaml"
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data.get("tables", [])


def load_entity_relationships() -> List[Dict[str, Any]]:
    """Load entity_relationships_corrected.yaml join path graph."""
    path = METADATA_DIR / "entity_relationships_corrected.yaml"
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data.get("relationships", [])


def load_table_column_docs() -> Dict[str, Any]:
    """Load table_column_docs.yaml and map table_name -> doc dict."""
    path = METADATA_DIR / "table_column_docs.yaml"
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    mapped = {}
    for entry in data.get("tables", []):
        t_name = entry.get("table")
        if t_name:
            mapped[t_name] = entry
    return mapped


DOMAIN_TAGS_DATA = load_domain_tags()
RELATIONSHIPS_DATA = load_entity_relationships()
COLUMN_DOCS_DATA = load_table_column_docs()


def get_candidate_tables_for_domains(domains: List[str]) -> Set[str]:
    """Find tables whose domain_tags overlap matched domains."""
    domain_set = set(domains)
    candidates = set()
    for entry in DOMAIN_TAGS_DATA:
        t_domains = set(entry.get("domain_tags", []))
        if t_domains.intersection(domain_set):
            candidates.add(entry.get("table"))
    return candidates


def bfs_expand_relationships(start_tables: Set[str], max_hops: int = 2) -> Set[str]:
    """BFS graph expansion over entity_relationships_corrected."""
    expanded = set(start_tables)
    queue = deque([(t, 0) for t in start_tables])
    
    # Build bi-directional adjacency lookup
    adj = {}
    for rel in RELATIONSHIPS_DATA:
        f = rel["from_table"]
        t = rel["to_table"]
        if f not in adj: adj[f] = set()
        if t not in adj: adj[t] = set()
        adj[f].add(t)
        adj[t].add(f)
        
    while queue:
        table, hops = queue.popleft()
        if hops >= max_hops:
            continue
        neighbors = adj.get(table, set())
        for n in neighbors:
            if n not in expanded:
                expanded.add(n)
                queue.append((n, hops + 1))
                
    return expanded


def get_join_path_descriptions(tables: Set[str]) -> List[Dict[str, Any]]:
    """Extract relevant relationship edges between shortlisted tables."""
    relevant_edges = []
    for rel in RELATIONSHIPS_DATA:
        if rel["from_table"] in tables and rel["to_table"] in tables:
            relevant_edges.append(rel)
    return relevant_edges


def assemble_schema_context(tables: Set[str], role: str) -> str:
    """Build readable natural-language schema documentation for shortlisted tables."""
    view_dataset = f"views_{role}"
    lines = [f"Database Schema Context (Execute queries against `{view_dataset}` view dataset):", ""]
    
    for t_name in sorted(tables):
        doc_entry = COLUMN_DOCS_DATA.get(t_name, {})
        t_desc = doc_entry.get("table_description", "No description available.")
        lines.append(f"Table: `{view_dataset}.{t_name}`")
        lines.append(f"Description: {t_desc}")
        lines.append("Columns:")
        
        cols = doc_entry.get("columns", [])
        if isinstance(cols, list):
            for col_info in cols:
                col_name = col_info.get("column", "")
                c_type = col_info.get("type", "STRING")
                c_desc = col_info.get("description", "")
                enums = col_info.get("literal_enum_values", [])
                enum_str = f" [Allowed values: {', '.join(map(repr, enums))}]" if enums else ""
                lines.append(f"  - `{col_name}` ({c_type}): {c_desc}{enum_str}")
        lines.append("")

        
    # Append join paths
    join_edges = get_join_path_descriptions(tables)
    if join_edges:
        lines.append("Allowed Join Relationships:")
        for edge in join_edges:
            f = edge["from_table"]
            fc = edge["from_column"]
            t = edge["to_table"]
            tc = edge["to_column"]
            rel_type = edge.get("relationship_type", "relates_to")
            flt = f" (filter: {edge['filter']})" if edge.get("filter") else ""
            lines.append(f"  - `{view_dataset}.{f}.{fc}` = `{view_dataset}.{t}.{tc}` [{rel_type}]{flt}")
        lines.append("")
        
    return "\n".join(lines)


def retrieval_node(state: GraphState) -> Dict[str, Any]:
    """LangGraph node executing candidate table retrieval and graph expansion."""
    start_time = time.time()
    session_id = state.get("session_id", "default")
    role = state.get("role", "unknown")
    matched_domains = state.get("final_domains", [])
    question = state.get("search_concept") or state.get("question", "")
    
    candidates = set()
    
    # 3a: Call hybrid vector + keyword table retrieval if available
    if retrieve_relevant_tables is not None:
        try:
            rel_tables = retrieve_relevant_tables(
                question=question,
                domain=matched_domains,
                user_role=role,
                hybrid=True
            )
            for item in rel_tables:
                if isinstance(item, dict) and "table_name" in item:
                    candidates.add(item["table_name"])
        except Exception as e:
            candidates = set()

    if not candidates:
        candidates = get_candidate_tables_for_domains(matched_domains)
    
    if not candidates:
        candidates = {"customers", "loans", "employees", "branches"}
        
    final_tables = candidates
    
    # 3b: Schema context assembly
    schema_text = assemble_schema_context(final_tables, role)
    join_paths = get_join_path_descriptions(final_tables)
    
    res = {
        "retrieved_tables": sorted(list(final_tables)),
        "join_paths": join_paths,
        "schema_context": schema_text,
    }
    
    DEFAULT_LOGGING_STORE.log_stage(
        session_id=session_id,
        role=role,
        turn_index=0,
        stage="retrieval",
        input_data=matched_domains,
        output_data=res["retrieved_tables"],
        success=True,
        latency_ms=(time.time() - start_time) * 1000,
        extra_fields={"table_count": len(final_tables)}
    )
    return res
