"""
api/main.py — Main FastAPI Application Entry Point for MSAI Service.
Includes router mounting, CORS middleware, health probe, and IAM startup checks.
"""

import sys
import logging
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Ensure repo root is on sys.path
REPO_ROOT = Path(__file__).parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import config
from bq_client import PROJECT_ID, get_client
from api.routes.chat import router as chat_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("msai.api")


def run_startup_security_checks():
    """
    Perform AGENT_ARCHITECTURE.md §6/§7 Startup Checks.
    Validates BigQuery connectivity and IAM role-scoped view dataset enforcement.
    """
    logger.info("==================================================")
    logger.info("MSAI FASTAPI SERVICE — RUNNING STARTUP CHECKS")
    logger.info(f"Target BigQuery Project ID: {PROJECT_ID}")
    logger.info("==================================================")
    
    app_env = config.os.environ.get("APP_ENV", "development").lower()
    
    try:
        bq_client = get_client()
        datasets = [d.dataset_id for d in bq_client.list_datasets()]
        view_datasets = [d for d in datasets if d.startswith("views_")]
        
        logger.info(f"Detected BigQuery Datasets: {len(datasets)} total, {len(view_datasets)} role-scoped view datasets.")
        
        if not view_datasets:
            warn_msg = (
                "CRITICAL WARNING: No 'views_<role>' datasets detected in BigQuery! "
                "The system requires datasets like 'views_executive', 'views_loan_officer', etc. "
                "Ensure dataset views creation scripts have been executed."
            )
            if app_env == "production":
                logger.error(f"HARD BLOCK IN PRODUCTION: {warn_msg}")
                raise RuntimeError(warn_msg)
            else:
                logger.warning(f"DEV MODE WARNING: {warn_msg}")

        # IAM Authorized Views Enforcement Warning Banner
        banner = """
================================================================================
 [WARNING: DEV MODE UNENFORCED IAM BOUNDARY]
 Per-role BigQuery IAM Service Accounts have not been impersonated yet.
 Executing queries via application-level fallback default credentials.
 DO NOT USE IN PRODUCTION WITHOUT EXECUTING access_control/generated_role_grants.sh!
================================================================================
"""
        logger.warning(banner)
        
    except Exception as e:
        logger.error(f"Startup check warning: {str(e)}")
        if app_env == "production":
            raise e


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Run startup security checks
    run_startup_security_checks()
    yield
    logger.info("MSAI FastAPI Service shutting down...")


app = FastAPI(
    title="MSAI — Financial Data Chatbot API",
    description="Asynchronous multi-agent query generation, validation, and execution service built on LangGraph & BigQuery.",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS Middleware Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Routes
app.include_router(chat_router)


@app.get("/health", tags=["Health Probe"])
async def health_check():
    """Health readiness probe endpoint."""
    return {
        "status": "healthy",
        "service": "MSAI FastAPI Service",
        "project_id": PROJECT_ID,
    }
