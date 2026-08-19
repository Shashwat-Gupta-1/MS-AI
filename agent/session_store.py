"""
agent/session_store.py — Pluggable session & context storage interface.
Defines abstract SessionStore ABC and MemorySessionStore implementation
utilizing LangGraph MemorySaver checkpointer.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
import time
from langgraph.checkpoint.memory import MemorySaver


class SessionStore(ABC):
    """Abstract interface for session storage and chat history resolution."""
    
    @abstractmethod
    def get_session(self, user_id: str, session_id: str) -> Dict[str, Any]:
        """Fetch session metadata and prior turn history."""
        pass
    
    @abstractmethod
    def append_turn(
        self,
        user_id: str,
        session_id: str,
        question: str,
        sql_query: Optional[str],
        final_response: Any,
        matched_domains: List[str],
        retrieved_tables: List[str],
        schema_context: Optional[str] = None,
    ) -> None:
        """Append completed turn context to session state."""
        pass
    
    @abstractmethod
    def get_last_turn_timestamp(self, user_id: str, session_id: str) -> Optional[float]:
        """Return unix timestamp of the last message in session."""
        pass


class MemorySessionStore(SessionStore):
    """MVP Memory-backed session store using LangGraph MemorySaver pattern."""
    
    def __init__(self):
        self._store: Dict[str, Dict[str, Any]] = {}
        self.checkpointer = MemorySaver()
    
    def _key(self, user_id: str, session_id: str) -> str:
        return f"{user_id}:{session_id}"
    
    def get_session(self, user_id: str, session_id: str) -> Dict[str, Any]:
        key = self._key(user_id, session_id)
        if key not in self._store:
            self._store[key] = {
                "user_id": user_id,
                "session_id": session_id,
                "created_at": time.time(),
                "last_active_at": time.time(),
                "turns": [],
                "active_domains": [],
                "active_tables": [],
                "active_schema_context": "",
            }
        return self._store[key]
    
    def append_turn(
        self,
        user_id: str,
        session_id: str,
        question: str,
        sql_query: Optional[str],
        final_response: Any,
        matched_domains: List[str],
        retrieved_tables: List[str],
        schema_context: Optional[str] = None,
    ) -> None:
        session = self.get_session(user_id, session_id)
        now = time.time()
        session["last_active_at"] = now
        session["turns"].append({
            "timestamp": now,
            "question": question,
            "sql_query": sql_query,
            "matched_domains": matched_domains,
            "retrieved_tables": retrieved_tables,
            "schema_context": schema_context,
        })
        if matched_domains:
            session["active_domains"] = matched_domains
        if retrieved_tables:
            session["active_tables"] = retrieved_tables
        if schema_context:
            session["active_schema_context"] = schema_context
    
    def get_last_turn_timestamp(self, user_id: str, session_id: str) -> Optional[float]:
        session = self.get_session(user_id, session_id)
        if session["turns"]:
            return session["turns"][-1]["timestamp"]
        return None


# Global singleton instance for MVP runtime
DEFAULT_SESSION_STORE = MemorySessionStore()
