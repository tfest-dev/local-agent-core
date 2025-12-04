# tools/__init__.py

from __future__ import annotations

from .base import Tool, ToolResult, ToolRegistry, tool_registry, ToolExecutor

# Import concrete tools so they self-register with the global registry.
from . import obsidian_notes  # noqa: F401

__all__ = [
    "Tool",
    "ToolResult",
    "ToolRegistry",
    "tool_registry",
    "ToolExecutor",
]
