# memory/store.py

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any

from .models import MemoryItem


class MemoryStore(ABC):
    """Abstract interface for a memory backend.

    Implementations hide the concrete storage system (OpenMemory, SQLite, etc.)
    behind a simple add/search interface.
    """

    @abstractmethod
    def add_interaction(
        self,
        user_text: str,
        assistant_text: str,
        *,
        user_id: Optional[str] = None,
        alias: Optional[str] = None,
        extra_metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Store a single user/assistant turn in memory.

        Implementations are free to compress or transform this interaction
        before persisting it.
        """

    @abstractmethod
    def search(
        self,
        query: str,
        *,
        user_id: Optional[str] = None,
        alias: Optional[str] = None,
        limit: int = 5,
    ) -> List[MemoryItem]:
        """Retrieve up to `limit` relevant memories for the given query."""
        raise NotImplementedError
