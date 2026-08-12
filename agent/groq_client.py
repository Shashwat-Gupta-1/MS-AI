import os
import time
import threading
from pathlib import Path
from typing import Optional, List, Any
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage, AIMessage

load_dotenv()




from config_guardrails import (
    DEFAULT_GROQ_MODEL,
    GROQ_RATE_LIMIT_BACKOFF_BASE,
    GROQ_MAX_RETRIES,
)


def _is_valid_key_format(key: str) -> bool:
    """Check if key is a non-placeholder string."""
    k = key.strip()
    if not k or len(k) < 15:
        return False
    if "your_" in k or "_here" in k or "placeholder" in k:
        return False
    return True


class GroqKeyRotator:
    """Thread-safe Round-Robin rotator for multiple Groq API keys with automatic failover."""

    def __init__(self):
        self._lock = threading.Lock()
        self._index = 0
        self._cached_keys: List[str] = []

    def get_all_keys(self) -> List[str]:
        if self._cached_keys:
            return self._cached_keys

        discovered_keys: List[str] = []

        # Priority 1: Direct Regex Extraction of all gsk_... keys in .env
        env_path = Path(__file__).resolve().parent.parent / ".env"
        if env_path.exists():
            try:
                import re
                with open(env_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                matches = re.findall(r"gsk_[A-Za-z0-9_-]+", content)
                for k in matches:
                    if k not in discovered_keys and _is_valid_key_format(k):
                        discovered_keys.append(k)
            except Exception:
                pass

        # Priority 2: GROQ_API_KEYS (comma-separated list in .env)
        raw_keys = os.environ.get("GROQ_API_KEYS", "").strip()
        if raw_keys:
            parsed = [k.strip() for k in raw_keys.split(",") if _is_valid_key_format(k)]
            for k in parsed:
                if k not in discovered_keys:
                    discovered_keys.append(k)

        # Priority 3: GROQ_API_KEY (single fallback key)
        single_key = os.environ.get("GROQ_API_KEY", "").strip()
        if _is_valid_key_format(single_key) and single_key not in discovered_keys:
            discovered_keys.append(single_key)

        with self._lock:
            self._cached_keys = discovered_keys

        return self._cached_keys

    def get_next_key(self) -> str:
        keys = self.get_all_keys()
        if not keys:
            raise ValueError(
                "No valid Groq API keys configured. Please set GROQ_API_KEYS=key1,key2... "
                "or GROQ_API_KEY=key in your .env file."
            )
        with self._lock:
            key = keys[self._index % len(keys)]
            self._index = (self._index + 1) % len(keys)
            return key


KEY_ROTATOR = GroqKeyRotator()


def get_groq_model(
    model_name: Optional[str] = None,
    temperature: float = 0.0,
    api_key: Optional[str] = None,
) -> ChatGroq:
    """Instantiate ChatGroq model using specified or rotated API key."""
    key = api_key or KEY_ROTATOR.get_next_key()
    selected_model = model_name or DEFAULT_GROQ_MODEL
    return ChatGroq(
        groq_api_key=key,
        model_name=selected_model,
        temperature=temperature,
        max_retries=1,  # Retries handled by key rotation
    )


def invoke_groq_with_retry(
    messages: List[BaseMessage],
    model_name: Optional[str] = None,
    temperature: float = 0.0,
) -> BaseMessage:
    """Invoke Groq LLM with Round-Robin key rotation and automatic failover on 429 rate limits and 401 invalid keys."""
    keys = KEY_ROTATOR.get_all_keys()
    if not keys:
        raise ValueError(
            "No valid Groq API keys configured. Please set GROQ_API_KEYS=key1,key2... "
            "or GROQ_API_KEY=key in your .env file."
        )

    total_attempts = max(len(keys) * 2, GROQ_MAX_RETRIES)

    for attempt in range(total_attempts):
        active_key = KEY_ROTATOR.get_next_key()
        # Fallback to llama-3.1-8b-instant if 70b hits daily TPD limit
        active_model = model_name or DEFAULT_GROQ_MODEL
        if attempt >= len(keys):
            active_model = "llama-3.1-8b-instant"

        try:
            llm = get_groq_model(model_name=active_model, temperature=temperature, api_key=active_key)
            return llm.invoke(messages)
        except Exception as e:
            err_str = str(e).lower()
            if any(k in err_str for k in ["rate_limit", "429", "quota", "tokens", "tpm", "tpd", "401", "invalid_api_key"]):
                # Sleep with exponential backoff on Groq rate limits
                backoff = min(8.0, GROQ_RATE_LIMIT_BACKOFF_BASE * (attempt + 1))
                time.sleep(backoff)
                if attempt == total_attempts - 1:
                    raise e
            else:
                if attempt == total_attempts - 1:
                    raise e
                time.sleep(0.5)


    llm = get_groq_model(model_name="llama-3.1-8b-instant", temperature=temperature)
    return llm.invoke(messages)





