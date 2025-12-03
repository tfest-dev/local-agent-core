# memory/openmemory_store.py

from __future__ import annotations

import os
import logging
from typing import Any, Dict, List, Optional

import requests

from .models import MemoryItem
from .store import MemoryStore

logger = logging.getLogger(__name__)


class OpenMemoryStore(MemoryStore):
    """MemoryStore implementation backed by an OpenMemory HTTP server.

    This assumes a running OpenMemory instance (see memory/OPEN_MEM_README.md)
    and talks to its `/memory/add` and `/memory/query` endpoints.
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8080",
        api_key: Optional[str] = None,
        timeout: int = 10,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout

    @classmethod
    def from_env(cls) -> "OpenMemoryStore":
        """Construct an OpenMemoryStore using common environment variables.

        - OPENMEMORY_URL / OM_BASE_URL: base URL of the OpenMemory backend
        - OPENMEMORY_API_KEY / OM_API_KEY: optional API key for auth
        """
        base_url = (
            os.getenv("OPENMEMORY_URL")
            or os.getenv("OM_BASE_URL")
            or "http://localhost:8080"
        )
        api_key = os.getenv("OPENMEMORY_API_KEY") or os.getenv("OM_API_KEY")
        return cls(base_url=base_url, api_key=api_key)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def add_interaction(
        self,
        user_text: str,
        assistant_text: str,
        *,
        user_id: Optional[str] = None,
        alias: Optional[str] = None,
        extra_metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        content = f"User: {user_text}\nAssistant: {assistant_text}"

        payload: Dict[str, Any] = {"content": content}

        if user_id:
            payload["user_id"] = user_id

        metadata: Dict[str, Any] = extra_metadata.copy() if extra_metadata else {}
        if alias:
            metadata.setdefault("alias", alias)
        if metadata:
            payload["metadata"] = metadata

        # Also project key metadata fields into the top-level `tags` array so
        # that they are immediately visible in the OpenMemory dashboard UI
        # without requiring custom views. This does not affect retrieval
        # semantics but makes domains/channels/session_kind easier to inspect.
        tags: List[str] = []
        domain = metadata.get("memory_domain")
        if domain:
            tags.append(str(domain))
        channel = metadata.get("channel")
        if channel:
            tags.append(str(channel))
        session_kind = metadata.get("session_kind")
        if session_kind:
            tags.append(str(session_kind))
        alias_tag = metadata.get("alias")
        if alias_tag:
            tags.append(str(alias_tag))
        if tags:
            payload["tags"] = tags

        self._post("/memory/add", json=payload)

    def search(
        self,
        query: str,
        *,
        user_id: Optional[str] = None,
        alias: Optional[str] = None,
        limit: int = 5,
    ) -> List[MemoryItem]:
        payload: Dict[str, Any] = {"query": query, "k": limit}

        filters: Dict[str, Any] = {}
        if user_id:
            filters["user_id"] = user_id
        if alias:
            filters["alias"] = alias
        if filters:
            payload["filters"] = filters

        data = self._post("/memory/query", json=payload)
        return self._parse_query_response(data)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            # OpenMemory expects an API key; support both Authorization and
            # x-api-key headers so it works with common deployments.
            headers["Authorization"] = f"Bearer {self.api_key}"
            headers["x-api-key"] = self.api_key
        return headers

    def _post(self, path: str, json: Dict[str, Any]) -> Any:
        url = f"{self.base_url}{path}"
        try:
            resp = requests.post(
                url, json=json, headers=self._headers(), timeout=self.timeout
            )
        except requests.RequestException as e:
            logger.error("OpenMemory request to %s failed: %s", url, e)
            raise

        if resp.status_code >= 400:
            logger.error(
                "OpenMemory request to %s failed with status %s: %s",
                url,
                resp.status_code,
                resp.text,
            )
        resp.raise_for_status()

        if not resp.content:
            return None
        try:
            return resp.json()
        except ValueError:
            return None

    def _parse_query_response(self, data: Any) -> List[MemoryItem]:
        if data is None:
            return []

        items: List[Dict[str, Any]] = []

        if isinstance(data, list):
            items = data
        elif isinstance(data, dict):
            for key in ("memories", "results", "items", "data"):
                if key in data and isinstance(data[key], list):
                    items = data[key]
                    break
            else:
                # Fallback if the server returns a single memory object.
                if any(k in data for k in ("content", "text")):
                    items = [data]

        results: List[MemoryItem] = []
        for raw in items:
            if not isinstance(raw, dict):
                continue
            content = (
                str(raw.get("content") or raw.get("text") or "")
            ).strip()
            if not content:
                continue
            mem_id = str(raw.get("id") or raw.get("memory_id") or "")
            score = raw.get("score") or raw.get("salience")
            metadata = raw.get("metadata") or {}
            if not isinstance(metadata, dict):
                metadata = {"raw_metadata": metadata}
            results.append(MemoryItem(id=mem_id, content=content, score=score, metadata=metadata))

        return results
