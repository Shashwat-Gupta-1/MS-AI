"""
agent/nodes/schema_retrieval.py — Column-Level Embedding Retrieval, LLM Anchor Reranking, & Shortest-Path Traversal.
Implements 4-step schema context assembly without flood-fill table over-expansion.
"""

import time
import json
import logging
from collections import deque
from typing import Dict, Any, List, Set, Tuple, Optional


from config import PROJECT_ID, METADATA_DATASET
from config_guardrails import (
    SCHEMA_RETRIEVAL_TOP_K,
    SCHEMA_RETRIEVAL_MAX_ANCHORS,
    SCHEMA_RETRIEVAL_MAX_PATH_HOPS,
    MAX_SCHEMA_CONTEXT_TOKENS,
    SCHEMA_RETRIEVAL_MODE,
)
from bq_client import get_client
from agent.groq_client import invoke_groq_with_retry
from agent.nodes.retrieval import (
    get_candidate_tables_for_domains,
    load_entity_relationships,
    assemble_schema_context,
)
from agent.state import GraphState
from agent.logging_store import DEFAULT_LOGGING_STORE
from langchain_core.messages import SystemMessage, HumanMessage

logger = logging.getLogger("msai.audit")

MODEL_ID = f"{PROJECT_ID}.{METADATA_DATASET}.text_embedding_model"
COLUMN_DOCS_TABLE = f"{PROJECT_ID}.{METADATA_DATASET}.column_docs"

RERANK_SYSTEM_PROMPT = """You are a Schema Reranking & Disambiguation Agent for a database analytics pipeline.
Given a User Question and a list of Candidate Columns retrieved via vector search, select only the columns strictly needed to answer the question, plus any Foreign Key join columns required to connect those tables.

For each selected column:
- Return the exact `table_name` and `column_name`.
- Assign `confidence`: "high" if unambiguous, or "low" if multiple columns (e.g. `disbursed_amount`, `sanctioned_amount`, `outstanding_amount`) could apply and the prompt does not specify.
- If `confidence` is "low", include a brief `clarification_needed` string describing the ambiguity.

Candidate Columns:
{candidate_columns_json}

User Question: "{question}"

Respond with ONLY a valid JSON object in the following format:
{{
  "selected_columns": [
    {{
      "table_name": "...",
      "column_name": "...",
      "reason": "...",
      "confidence": "high" | "low",
      "clarification_needed": "" | "..."
    }}
  ]
}}
"""


def vector_search_top_k_columns(question: str, candidate_tables: Set[str], top_k: int) -> List[Dict[str, Any]]:
    """Step 1: Perform vector similarity search against rag_meta.column_docs in BigQuery."""
    client = get_client()

    if not candidate_tables:
        return []

    tables_filter = list(candidate_tables)

    # Fetch question embedding and calculate cosine distance in BigQuery
    sql = f"""
    WITH q_emb AS (
      SELECT ml_generate_embedding_result AS emb
      FROM ML.GENERATE_EMBEDDING(
        MODEL `{MODEL_ID}`,
        (SELECT @question AS content)
      )
    )
    SELECT
      c.table_name,
      c.column_name,
      c.description,
      c.data_type,
      ML.DISTANCE(c.embedding, q.emb, 'COSINE') AS distance
    FROM `{COLUMN_DOCS_TABLE}` c, q_emb q
    WHERE c.table_name IN UNNEST(@candidate_tables)
      AND ARRAY_LENGTH(c.embedding) > 0
    ORDER BY distance ASC
    LIMIT {top_k}
    """

    from google.cloud.bigquery import ScalarQueryParameter, ArrayQueryParameter, QueryJobConfig
    params = [
        ScalarQueryParameter("question", "STRING", question),
        ArrayQueryParameter("candidate_tables", "STRING", tables_filter),
    ]
    job_config = QueryJobConfig(query_parameters=params)

    try:
        df = client.query(sql, job_config=job_config).to_dataframe()
        records = []
        for _, r in df.iterrows():
            # Convert cosine distance (0=identical, 2=opposite) to similarity score (1 = identical)
            dist = float(r["distance"])
            sim_score = max(0.0, 1.0 - (dist / 2.0))
            records.append({
                "table_name": r["table_name"],
                "column_name": r["column_name"],
                "description": r["description"] or "",
                "data_type": r["data_type"] or "STRING",
                "similarity_score": round(sim_score, 4),
            })
        return records
    except Exception as e:
        logger.warning(f"Vector search failed, returning empty candidates: {e}")
        return []


def llm_rerank_columns(question: str, candidate_cols: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], Set[str]]:
    """Step 2: LLM rerank candidate columns into selected columns and anchor tables."""
    if not candidate_cols:
        return [], set()

    cols_for_prompt = [
        {
            "table_name": c["table_name"],
            "column_name": c["column_name"],
            "description": c["description"],
            "score": c["similarity_score"],
        }
        for c in candidate_cols
    ]

    prompt = RERANK_SYSTEM_PROMPT.format(
        candidate_columns_json=json.dumps(cols_for_prompt, indent=2),
        question=question,
    )

    messages = [
        SystemMessage(content="You are a JSON-only schema reranking assistant."),
        HumanMessage(content=prompt),
    ]

    try:
        msg = invoke_groq_with_retry(messages, temperature=0.0)
        text = msg.content.strip()

        if text.startswith("```json"):
            text = text[7:]
        if text.endswith("```"):
            text = text[:-3]

        parsed = json.loads(text.strip())
        selected = parsed.get("selected_columns", [])
        anchors = {c["table_name"] for c in selected if "table_name" in c}

        if len(anchors) > SCHEMA_RETRIEVAL_MAX_ANCHORS:
            logger.warning(f"SCHEMA_RETRIEVAL_MAX_ANCHORS exceeded ({len(anchors)} > {SCHEMA_RETRIEVAL_MAX_ANCHORS})")

        return selected, anchors
    except Exception as e:
        logger.warning(f"LLM rerank failed: {e}")
        # Fallback to top-3 distinct candidate tables as anchors
        fallback_anchors = {c["table_name"] for c in candidate_cols[:5]}
        return candidate_cols, fallback_anchors


import heapq


def shortest_path_bfs(from_table: str, to_table: str, max_hops: int) -> Tuple[List[str], List[Dict[str, Any]]]:
    """Find weighted shortest path between two anchor tables up to max_hops using Dijkstra's algorithm.
    Edges derived via direct_ref have weight 1.0; edges derived via same_as_ref have weight 1.5.
    """
    relationships = load_entity_relationships()

    if from_table == to_table:
        return [from_table], []

    adj = {}
    edge_info = {}
    for rel in relationships:
        f, t = rel["from_table"], rel["to_table"]
        adj.setdefault(f, set()).add(t)
        adj.setdefault(t, set()).add(f)
        edge_info[(f, t)] = rel
        edge_info[(t, f)] = rel

    # Priority queue storing (cost, curr_node, path, filters)
    pq = [(0.0, from_table, [from_table], [])]
    visited_costs = {from_table: 0.0}

    while pq:
        curr_cost, curr, path, filters = heapq.heappop(pq)

        if curr == to_table:
            return path, filters

        if len(path) - 1 >= max_hops:
            continue

        for nbr in adj.get(curr, set()):
            rel = edge_info.get((curr, nbr), {})
            derivation = str(rel.get("derivation", "")).lower()
            edge_weight = 1.5 if "same_as_ref" in derivation else 1.0
            next_cost = curr_cost + edge_weight

            if nbr not in visited_costs or next_cost < visited_costs[nbr]:
                visited_costs[nbr] = next_cost
                new_filters = list(filters)
                if rel.get("filter"):
                    new_filters.append(rel)
                heapq.heappush(pq, (next_cost, nbr, path + [nbr], new_filters))

    return [], []



def connect_anchor_tables(anchors: Set[str], max_hops: int) -> Tuple[Set[str], List[Dict[str, Any]]]:
    """Step 3: Union pairwise shortest paths between all anchor tables."""
    anchors_list = sorted(list(anchors))
    connecting = set(anchors)
    propagated_filters = []

    for i in range(len(anchors_list)):
        for j in range(i + 1, len(anchors_list)):
            t1, t2 = anchors_list[i], anchors_list[j]
            path, filters = shortest_path_bfs(t1, t2, max_hops=max_hops)

            if not path:
                logger.warning(f"anchor_pair_unreachable: No path between `{t1}` and `{t2}` within {max_hops} hops.")
                DEFAULT_LOGGING_STORE.log_stage(
                    session_id="schema_retrieval",
                    role="system",
                    turn_index=0,
                    stage="anchor_pair_unreachable",
                    input_data={"t1": t1, "t2": t2},
                    output_data={"max_hops": max_hops},
                    success=False,
                    latency_ms=0.0,
                )
            else:
                connecting.update(path)
                propagated_filters.extend(filters)

    return connecting, propagated_filters


def estimate_tokens(text: str) -> int:
    """Rough token estimation (4 chars per token)."""
    return len(text) // 4


def trim_schema_tables(
    tables: Set[str], anchors: Set[str], role: str, max_tokens: int
) -> Tuple[Set[str], Optional[Dict[str, Any]]]:
    """Step 4: Trim non-anchor bridge tables furthest from anchors if schema text exceeds token cap."""
    curr_tables = set(tables)
    schema_text = assemble_schema_context(curr_tables, role)
    curr_tokens = estimate_tokens(schema_text)

    if curr_tokens <= max_tokens:
        return curr_tables, None

    # Calculate distance from closest anchor for each non-anchor table
    non_anchors = curr_tables - anchors
    distances = {}

    for t in non_anchors:
        min_d = 999
        for anc in anchors:
            path, _ = shortest_path_bfs(anc, t, max_hops=5)
            if path:
                min_d = min(min_d, len(path) - 1)
        distances[t] = min_d

    # Sort non-anchors by distance descending (furthest first)
    sorted_candidates = sorted(non_anchors, key=lambda x: distances[x], reverse=True)
    trimmed_tables = []

    for t_remove in sorted_candidates:
        curr_tables.remove(t_remove)
        trimmed_tables.append(t_remove)
        schema_text = assemble_schema_context(curr_tables, role)
        if estimate_tokens(schema_text) <= max_tokens:
            break

    trim_log = {
        "initial_tokens": curr_tokens,
        "final_tokens": estimate_tokens(schema_text),
        "trimmed_tables": trimmed_tables,
    }
    return curr_tables, trim_log


def schema_retrieval_node(state: GraphState) -> Dict[str, Any]:
    """LangGraph node executing column RAG retrieval, LLM anchor reranking, and shortest-path traversal."""
    start_time = time.time()
    session_id = state.get("session_id", "default")
    role = state.get("role", "unknown")
    question = state.get("question", "")
    matched_domains = state.get("final_domains", [])

    # Step 1: Column vector search
    candidate_tables = get_candidate_tables_for_domains(matched_domains)
    cand_columns = vector_search_top_k_columns(question, candidate_tables, top_k=SCHEMA_RETRIEVAL_TOP_K)

    # Step 2: LLM rerank into anchors
    reranked_cols, anchors = llm_rerank_columns(question, cand_columns)

    if not anchors and candidate_tables:
        anchors = set(list(candidate_tables)[:3])

    # Step 3: Shortest-path traversal
    connecting_tables, prop_filters = connect_anchor_tables(anchors, max_hops=SCHEMA_RETRIEVAL_MAX_PATH_HOPS)

    # Step 4: Token budget trim
    final_tables, trim_log = trim_schema_tables(
        connecting_tables, anchors, role, max_tokens=MAX_SCHEMA_CONTEXT_TOKENS
    )
    final_schema_context = assemble_schema_context(final_tables, role)

    latency_ms = (time.time() - start_time) * 1000

    res = {
        "anchor_tables": sorted(list(anchors)),
        "candidate_columns": cand_columns,
        "reranked_columns": reranked_cols,
        "connecting_tables": sorted(list(connecting_tables)),
        "propagated_filters": prop_filters,
        "schema_trim_log": trim_log,
        "schema_retrieval_mode": SCHEMA_RETRIEVAL_MODE,
        "retrieved_tables": sorted(list(final_tables)),
        "schema_context": final_schema_context,
    }

    DEFAULT_LOGGING_STORE.log_stage(
        session_id=session_id,
        role=role,
        turn_index=0,
        stage="schema_retrieval",
        input_data={"question": question, "domains": matched_domains},
        output_data={
            "anchors": res["anchor_tables"],
            "connecting": res["connecting_tables"],
            "mode": SCHEMA_RETRIEVAL_MODE,
            "trim_log": trim_log,
        },
        success=True,
        latency_ms=latency_ms,
    )

    return res
