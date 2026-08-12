"""
agent/logging_store.py — Pluggable structured audit logging store interface.
Defines abstract LoggingStore ABC and JSONLLoggingStore implementation
writing per-stage log entries to logs/<role>/<session_id>.jsonl.
"""

from abc import ABC, abstractmethod
import json
import time
from pathlib import Path
from typing import Dict, Any, Optional

import logging
from config import LOGS_DIR



class LoggingStore(ABC):
    """Abstract interface for structured audit logging."""
    
    @abstractmethod
    def log_stage(
        self,
        session_id: str,
        role: str,
        turn_index: int,
        stage: str,
        input_data: Any,
        output_data: Any,
        success: bool,
        failure_reason: Optional[str] = None,
        latency_ms: Optional[float] = None,
        llm_model: Optional[str] = None,
        tokens_used: Optional[Dict[str, int]] = None,
        extra_fields: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Record structured log entry for a single pipeline stage."""
        pass


class JSONLLoggingStore(LoggingStore):
    """MVP file-backed JSONL logger partitioned by role and session_id."""
    
    def log_stage(
        self,
        session_id: str,
        role: str,
        turn_index: int,
        stage: str,
        input_data: Any,
        output_data: Any,
        success: bool,
        failure_reason: Optional[str] = None,
        latency_ms: Optional[float] = None,
        llm_model: Optional[str] = None,
        tokens_used: Optional[Dict[str, int]] = None,
        extra_fields: Optional[Dict[str, Any]] = None,
    ) -> None:
        role_dir = LOGS_DIR / (role or "unknown_role")
        role_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = role_dir / f"{session_id}.jsonl"
        
        entry = {
            "timestamp": time.time(),
            "session_id": session_id,
            "role": role,
            "turn_index": turn_index,
            "stage": stage,
            "input": str(input_data) if input_data is not None else None,
            "output": str(output_data) if output_data is not None else None,
            "success": success,
            "failure_reason": failure_reason,
            "latency_ms": latency_ms,
            "llm_model": llm_model,
            "tokens_used": tokens_used,
        }
        
        if extra_fields:
            entry.update(extra_fields)
            
        with open(file_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

        # Live terminal output (unbuffered for Uvicorn & Streamlit terminals)
        status_str = "SUCCESS" if success else f"FAILED ({failure_reason or 'Error'})"
        model_str = f" model={llm_model}" if llm_model else ""
        lat_str = f" {latency_ms:.1f}ms" if latency_ms is not None else ""
        log_line = f"[AUDIT LOG] [{stage.upper()}] session={session_id} role={role} status={status_str}{model_str}{lat_str}"
        
        print(log_line, flush=True)
        logging.getLogger("msai.audit").info(log_line)




# Global singleton logger instance for MVP
DEFAULT_LOGGING_STORE = JSONLLoggingStore()
