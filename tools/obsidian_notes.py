# tools/obsidian_notes.py

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime
from typing import Any, List

from .base import Tool, ToolResult, tool_registry


@dataclass
class ObsidianNoteConfig:
    """Configuration for the Obsidian note tool.

    The vault path is taken from the `OBSIDIAN_VAULT_PATH` environment
    variable; notes are written into a `local-agent-core/` subdirectory
    by default.
    """

    env_var: str = "OBSIDIAN_VAULT_PATH"
    subdir: str = "local-agent-core"


class ObsidianNoteTool(Tool):
    """Write a simple Markdown note into an Obsidian vault.

    This is intentionally conservative:
    - If `OBSIDIAN_VAULT_PATH` is not set, it does nothing and returns a
      non-fatal ToolResult.
    - It only ever *creates* new files under a configurable subdirectory
      (no modification or deletion of existing notes).
    """

    name = "obsidian_note"
    categories: List[str] = ["notes", "knowledge", "filesystem"]

    def __init__(self, config: ObsidianNoteConfig | None = None) -> None:
        self.config = config or ObsidianNoteConfig()

    def run(self, state: Any) -> ToolResult:
        base = os.getenv(self.config.env_var)
        if not base:
            return ToolResult(
                tool_name=self.name,
                success=False,
                summary=(
                    f"{self.config.env_var} not set; skipping Obsidian note "
                    "creation."
                ),
                details={"env_var": self.config.env_var},
            )

        vault_dir = os.path.join(base, self.config.subdir)
        os.makedirs(vault_dir, exist_ok=True)

        ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"agent-note-{ts}.md"
        path = os.path.join(vault_dir, filename)

        # We assume `state` follows the TurnState shape from agent.core.
        text = getattr(state, "text", "")
        alias = getattr(state, "alias_name", "unknown")
        interpreter = getattr(state, "interpreter", None)

        lines: List[str] = []
        lines.append(f"# Local Agent Note ({alias})")
        lines.append("")
        lines.append("## User Input")
        lines.append(text or "[empty]")
        lines.append("")

        if interpreter is not None:
            lines.append("## Interpreter Summary")
            intent = getattr(interpreter, "intent", "")
            summary = getattr(interpreter, "summary", "")
            if intent:
                lines.append(f"**Intent:** {intent}")
            if summary:
                lines.append("")
                lines.append(summary)
            lines.append("")

        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        return ToolResult(
            tool_name=self.name,
            success=True,
            summary=f"Wrote Obsidian note {filename}.",
            details={"path": path},
        )


# Register the tool in the global registry on import.
tool_registry.register(ObsidianNoteTool())
