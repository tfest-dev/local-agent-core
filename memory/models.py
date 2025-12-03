# memory/models.py

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class MemoryItem:
    """Represents a single retrieved memory item.

    This is intentionally minimal and backend-agnostic. Additional fields from
    OpenMemory are stored in `metadata` so they remain available for future
    use (e.g. salience, sector, timestamps).
    """

    id: str
    content: str
    score: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
