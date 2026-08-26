"""
retrieval.py
------------
Retrieval layer for RAG chatbot. Searches BigQuery metadata using Vector Search
and hybrid scoring (semantic + keyword overlap) to retrieve relevant tables
for a user's question, scoped by their role and domain.

Usage:
    from rag_setup.retrieval import retrieve_relevant_tables
    results = retrieve_relevant_tables(
        question="How many loans were disbursed last month?",
        domain="loan",
        user_role="loan_officer",
        top_k=3
    )
"""

import re
from google.cloud import bigquery

PROJECT_ID = "project-f118f2cb-f557-4d4f-990"
DATASET    = "rag_meta"

# Standard english stop words to ignore during keyword scoring
STOP_WORDS = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and",
    "any", "are", "aren't", "as", "at", "be", "because", "been", "before", "being",
    "below", "between", "both", "but", "by", "can", "can't", "cannot", "could",
    "couldn't", "did", "didn't", "do", "does", "doesn't", "doing", "don't", "down",
    "during", "each", "few", "for", "from", "further", "had", "hadn't", "has",
    "hasn't", "have", "haven't", "having", "he", "he'd", "he'll", "he's", "her",
    "here", "here's", "hers", "herself", "him", "himself", "his", "how", "how's",
    "i", "i'd", "i'll", "i'm", "i've", "if", "in", "into", "is", "isn't", "it",
    "it's", "its", "itself", "let's", "me", "more", "most", "mustn't", "my",
    "myself", "no", "nor", "not", "of", "off", "on", "once", "only", "or", "other",
    "ought", "our", "ours", "ourselves", "out", "over", "own", "same", "shan't",
    "she", "she'd", "she'll", "she's", "should", "shouldn't", "so", "some", "such",
    "than", "that", "that's", "the", "their", "theirs", "them", "themselves",
    "then", "there", "there's", "these", "they", "they'd", "they'll", "they're",
    "they've", "this", "those", "through", "to", "too", "under", "until", "up",
    "very", "was", "wasn't", "we", "we'd", "we'll", "we're", "we've", "were",
    "weren't", "what", "what's", "when", "when's", "where", "where's", "which",
    "while", "who", "who's", "whom", "why", "why's", "with", "won't", "would",
    "wouldn't", "you", "you'd", "you'll", "you're", "you've", "your", "yours",
    "yourself", "yourselves"
}


def _tokenize(text: str) -> set[str]:
    """Tokenize text into a set of lowercased alphanumeric words, ignoring stop words."""
    if not text:
        return set()
    words = re.findall(r"\b[a-zA-Z0-9_]+\b", text.lower())
    return {w for w in words if w not in STOP_WORDS}


def _calculate_keyword_score(question_tokens: set[str], table_name: str, description: str, chunk_texts: str = "") -> float:
    """Calculate Jaccard-like overlap score between question tokens and table name + description + chunk texts."""
    if not question_tokens:
        return 0.0

    table_text = f"{table_name} {description or ''} {chunk_texts or ''}"
    table_tokens = _tokenize(table_text)

    overlap = question_tokens.intersection(table_tokens)
    return len(overlap) / len(question_tokens)


def retrieve_relevant_tables(
    question: str,
    domain: str | list[str],
    user_role: str,
    top_k: int = None,
    hybrid: bool = True,
    semantic_weight: float = 0.6,
    confidence_gap: float = 0.05
) -> list[dict]:
    """
    Search table_embeddings using Vector Search, filter to user's views_{user_role}
    dataset, and optionally apply a keyword-overlap hybrid score.

    Args:
        question: User's question to retrieve tables for.
        domain: Specific domain (e.g. 'loan') to filter tables.
        user_role: Role of the user querying (e.g. 'loan_officer').
        top_k: Number of relevant tables to return.
        hybrid: Whether to calculate hybrid scores combining Vector and Keyword scores.
        semantic_weight: Float weight for semantic vector similarity in hybrid score.
        confidence_gap: Confidence threshold gap between rank 1 and rank 2 to detect ambiguity.

    Returns:
        List of dicts: [
          {
            "dataset_name": "views_loan_officer",
            "table_name": "loans",
            "description": "Table description...",
            "score": 0.85,
            "ambiguous": True  # Only set on top result if confidence gap is not met
          }, ...
        ]
    """
    # 1. Validation to prevent SQL injection in dataset name
    if not re.match(r"^[a-zA-Z0-9_]+$", user_role):
        raise ValueError(f"Invalid user_role: {user_role}")

    client = bigquery.Client(project=PROJECT_ID)

    # Scoped dataset name
    role_dataset = f"views_{user_role}"

    # 2. BigQuery Vector Search query.
    sql = f"""
    SELECT
      search_results.base.table_id AS table_name,
      dt.table_description,
      STRING_AGG(search_results.base.chunk_text, " ") AS chunk_texts,
      MIN(search_results.distance) AS distance
    FROM VECTOR_SEARCH(
      TABLE `{PROJECT_ID}.{DATASET}.table_chunks`,
      'embedding',
      (
        SELECT ml_generate_embedding_result FROM ML.GENERATE_EMBEDDING(
          MODEL `{PROJECT_ID}.{DATASET}.text_embedding_model`,
          (SELECT @question as content),
          STRUCT(TRUE AS flatten_json_output, 'RETRIEVAL_QUERY' AS task_type)
        )
      ),
      top_k => 1000
    ) AS search_results
    JOIN `{PROJECT_ID}.{role_dataset}.INFORMATION_SCHEMA.TABLES` AS vt
      ON search_results.base.table_id = vt.table_name
    LEFT JOIN `{PROJECT_ID}.{DATASET}.domain_tags` AS dt
      ON search_results.base.dataset_id = dt.dataset_name AND search_results.base.table_id = dt.table_name
    WHERE
      (ARRAY_LENGTH(@candidate_tables) = 0 OR search_results.base.table_id IN UNNEST(@candidate_tables))
    GROUP BY
      search_results.base.table_id, dt.table_description
    """

    if isinstance(domain, str):
        domains = [domain]
    else:
        domains = domain

    # Fetch candidate tables from local domain_tags.yaml based on the selected domains
    candidate_tables = []
    if domains:
        try:
            import yaml
            from pathlib import Path
            yaml_path = Path("metadata/domain_tags.yaml")
            if yaml_path.exists():
                with open(yaml_path, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                    domain_set = set(domains)
                    for entry in data.get("tables", []):
                        t_domains = set(entry.get("domain_tags", []))
                        if t_domains.intersection(domain_set):
                            candidate_tables.append(entry.get("table"))
        except Exception as e:
            print(f"Warning: Failed to fetch candidate tables from yaml: {e}")

    query_params = [
        bigquery.ScalarQueryParameter("question", "STRING", question),
        bigquery.ArrayQueryParameter("candidate_tables", "STRING", candidate_tables),
    ]

    job_config = bigquery.QueryJobConfig(query_parameters=query_params)
    query_job = client.query(sql, job_config=job_config)
    rows = list(query_job.result())

    # 3. Calculate scores
    question_tokens = _tokenize(question)
    results = []

    for row in rows:
        table_name = row["table_name"]
        description = row["table_description"]
        chunk_texts = row["chunk_texts"]
        distance = row["distance"]

        # Convert cosine distance (0 to 2) to cosine similarity (0 to 1)
        semantic_score = max(0.0, 1.0 - distance)

        if hybrid:
            keyword_score = _calculate_keyword_score(question_tokens, table_name, description, chunk_texts)
            score = (semantic_weight * semantic_score) + ((1.0 - semantic_weight) * keyword_score)
        else:
            score = semantic_score

        results.append({
            "dataset_name": role_dataset,
            "table_name": table_name,
            "description": description,
            "score": round(score, 4),
            "semantic_score": round(semantic_score, 4),
            "distance": round(distance, 4),
            "keyword_score": round(keyword_score, 4)
        })

    # Sort by score descending
    results.sort(key=lambda x: x["score"], reverse=True)

    # Slice to top_k if specified
    if top_k is not None:
        final_results = results[:top_k]
    else:
        final_results = results

    # 4. Confidence / Ambiguity Check
    if len(final_results) >= 2:
        top_score = final_results[0]["score"]
        second_score = final_results[1]["score"]
        if (top_score - second_score) < confidence_gap:
            final_results[0]["ambiguous"] = True

    return final_results
