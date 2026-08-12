"""
config.py — single place every other module pulls project/environment
config from. Nothing else in the codebase should read os.environ directly
or hardcode a project ID — import PROJECT_ID from here instead, so there's
exactly one place to change when switching projects (dev -> prod, etc).
"""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

try:
    PROJECT_ID = os.environ["GCP_PROJECT_ID"]
except KeyError:
    raise RuntimeError(
        "GCP_PROJECT_ID is not set. Copy .env.example to .env (if present) "
        "or create a .env file with:\n\n  GCP_PROJECT_ID=your-project\n"
    )

# Repo-relative paths, so every script works regardless of the directory
# it's actually run from -- avoids the exact "relative path only works if
# you cd into the right folder" bug we hit in role_filter.py.
REPO_ROOT = Path(__file__).parent
SYSTEMS_DIR = REPO_ROOT / "systems"
OUTPUT_DIR = REPO_ROOT / "output"
METADATA_DIR = REPO_ROOT / "metadata"
SQL_DIR = REPO_ROOT / "sql"
ACCESS_CONTROL_DIR = REPO_ROOT / "access_control"
AGENT_DIR = REPO_ROOT / "agent"
CONFIG_DIR = REPO_ROOT / "config"
LOGS_DIR = REPO_ROOT / "logs"
FRONTEND_DIR = REPO_ROOT / "frontend"

# Dataset names -- single source of truth, referenced by scripts/create_datasets.py,
# scripts/create_tables.py, and anything else that needs to enumerate them.
BUSINESS_DATASETS = [
    "base", "los", "lms", "incentive", "zoho",
    "crm", "treasury", "insurance", "compliance", "support",
]
METADATA_DATASET = "rag_meta"
ALL_DATASETS = BUSINESS_DATASETS + [METADATA_DATASET]

