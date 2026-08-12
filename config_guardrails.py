"""
config_guardrails.py — Central source of truth for all guardrail thresholds,
retry limits, model choices, and configurable limits across the runtime agent.
No magic numbers should be hardcoded inside agent nodes.
"""

# Groq LLM Configuration
DEFAULT_GROQ_MODEL = "llama-3.3-70b-versatile"
GROQ_RATE_LIMIT_BACKOFF_BASE = 2.0  # seconds
GROQ_MAX_RETRIES = 3

# Query Validation & Execution Caps
MAX_BYTES_BILLED_CAP = 500 * 1024 * 1024  # 500 MB limit for BigQuery dry-runs
MAX_ROW_COUNT_CAP = 10000                 # Maximum allowed rows if unbounded
MAX_VALIDATION_RETRIES = 3                # Maximum SQL regeneration retries on failure

# Summarization Chunker Config
SUMMARIZATION_CHUNK_ROW_SIZE = 200        # Rows per chunk for Map-Reduce summarization

# Conversation Router Config
FOLLOWUP_TIME_GAP_THRESHOLD_SECONDS = 600 # 10 minutes gap threshold for Case B vs Case C fallback

# Schema Retrieval & Anchor-Based RAG Parameters
SCHEMA_RETRIEVAL_TOP_K = 20
SCHEMA_RETRIEVAL_MAX_ANCHORS = 6
SCHEMA_RETRIEVAL_MAX_PATH_HOPS = 3
MAX_SCHEMA_CONTEXT_TOKENS = 3000
SCHEMA_RETRIEVAL_MODE = "advisory"       # "advisory" or "enforcing"
RETRIEVAL_BFS_MAX_HOPS = 1

