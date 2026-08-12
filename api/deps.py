"""
api/deps.py — FastAPI dependencies for server-side auth, role resolution,
and shared session / logging store injection.
"""

import os
import json
from typing import Tuple, Dict
from fastapi import Request, HTTPException, Security, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from agent.session_store import DEFAULT_SESSION_STORE, SessionStore
from agent.logging_store import DEFAULT_LOGGING_STORE, LoggingStore

# Default MVP Token Table mapping Bearer tokens to (user_id, role)
DEFAULT_TOKEN_MAP: Dict[str, Tuple[str, str]] = {
    "token_executive": ("analyst_exec_01", "executive"),
    "token_loan_officer": ("loan_officer_01", "loan_officer"),
    "token_hr_officer": ("hr_officer_01", "hr_officer"),
    "token_collections_agent": ("collections_agent_01", "collections_agent"),
}


def load_token_map() -> Dict[str, Tuple[str, str]]:
    """Load token map from env override API_TOKENS_JSON if present, else fallback to default MVP map."""
    env_tokens = os.environ.get("API_TOKENS_JSON")
    if env_tokens:
        try:
            raw = json.loads(env_tokens)
            parsed = {}
            for tok, info in raw.items():
                if isinstance(info, list) and len(info) == 2:
                    parsed[tok] = (info[0], info[1])
            if parsed:
                return parsed
        except Exception:
            pass
    return DEFAULT_TOKEN_MAP


TOKEN_MAP = load_token_map()
security_bearer = HTTPBearer(auto_error=False)


async def get_current_user_and_role(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Security(security_bearer),
) -> Tuple[str, str]:
    """
    FastAPI security dependency for server-side user identity and role resolution.
    NEVER accepts role from request body. Must be asserted server-side.
    Returns (user_id, role).
    """
    token = None
    if credentials:
        token = credentials.credentials
    else:
        # Fallback to custom header or query param for CLI / curl convenience
        token = request.headers.get("X-API-Key") or request.query_params.get("api_key")

    if not token or token not in TOKEN_MAP:
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing authentication credentials. Provide 'Authorization: Bearer <token>' or 'X-API-Key' header.",
        )
        
    user_id, role = TOKEN_MAP[token]
    return user_id, role


def get_session_store() -> SessionStore:
    """Dependency injecting shared SessionStore interface."""
    return DEFAULT_SESSION_STORE


def get_logging_store() -> LoggingStore:
    """Dependency injecting shared LoggingStore interface."""
    return DEFAULT_LOGGING_STORE
