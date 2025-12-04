# tools/base.py

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class ToolResult:
    """Represents the outcome of running a tool.

    This is intentionally simple so it can be serialised to logs or
    passed into the narrator as part of internal context.
    """

    tool_name: str
    success: bool
    summary: str
    details: Dict[str, Any]


class Tool:
    """Base interface for all tools.

    Tools should be side-effect aware and conservative. They receive a
    `state` object (typically `TurnState` from `agent.core`) but are not
    coupled to its concrete type here to avoid circular imports.
    """

    # Human-readable name for logging / debugging.
    name: str = "tool"
    # High-level categories this tool belongs to (e.g. "email",
    # "workflow", "notes", "http"). Used by simple planners.
    categories: List[str] = []

    def run(self, state: Any) -> ToolResult:  # pragma: no cover - interface
        raise NotImplementedError


class ToolRegistry:
    """In-process registry for available tools.

    This keeps things simple for now; a future version could support
    dynamic loading, discovery, or sandboxing.
    """

    def __init__(self) -> None:
        self._tools: Dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> Optional[Tool]:
        return self._tools.get(name)

    def all(self) -> List[Tool]:
        return list(self._tools.values())

    def get_by_category(self, category: str) -> List[Tool]:
        category = category.lower()
        return [
            t
            for t in self._tools.values()
            if any(category == c.lower() for c in (t.categories or []))
        ]


# Global registry instance used by the agent.
tool_registry = ToolRegistry()


class ToolExecutor:
    """Minimal executor that runs tools based on a ToolPlan and channel.

    Execution policy (initial):
    - If `plan` is falsy or does not require tools, nothing is executed.
    - For non-automation channels, tools are not executed; instead a
      synthetic planning-only result is returned for transparency.
    - For `channel == "automation"`, tools are looked up by category and
      executed in-process.
    """

    def __init__(self, registry: ToolRegistry | None = None) -> None:
        self.registry = registry or tool_registry

    def execute(
        self,
        plan: Any,
        state: Any,
        *,
        channel: str,
        interactive_allowed: Optional[List[str]] = None,
    ) -> List[ToolResult]:
        from agent.core import ToolPlan  # imported lazily to avoid cycles

        if not isinstance(plan, ToolPlan) or not plan.needs_tools:
            return []

        categories = plan.categories or []

        # For interactive channels, only allow tools whose categories are
        # explicitly whitelisted via router configuration. Everything
        # else remains planning-only.
        if channel != "automation":
            allowed = {c.lower() for c in (interactive_allowed or [])}
            exec_categories = [
                c for c in categories if c.lower() in allowed
            ]
            if not exec_categories:
                return [
                    ToolResult(
                        tool_name="__planning_only__",
                        success=True,
                        summary=(
                            "Tools planned but not executed for non-automation "
                            f"channel '{channel}'."
                        ),
                        details={"categories": categories},
                    )
                ]
            # Restrict the categories we execute to the allowed subset.
            categories = exec_categories

        results: List[ToolResult] = []

        for cat in categories:
            tools = self.registry.get_by_category(cat)
            for tool in tools:
                try:
                    res = tool.run(state)
                except Exception as exc:  # pragma: no cover - defensive
                    res = ToolResult(
                        tool_name=tool.name,
                        success=False,
                        summary=f"Tool raised exception: {exc}",
                        details={"category": cat},
                    )
                results.append(res)

        return results
