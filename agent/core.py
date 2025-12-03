# agent/core.py

from typing import Optional, List

from inference import LLMRunner, route, get_router_alias_config
from prompts import build_prompt
from memory import MemoryStore, MemoryItem


class Agent:
    """Core agent abstraction for local-agent-core.

    This wraps routing, prompt construction, and LLM invocation behind a
    simple `respond` method so frontends (CLI, web UI, future voice UI)
    all share the same request flow.
    """

    def __init__(
        self,
        default_alias: str = "general",
        debug: bool = True,
        memory_store: Optional[MemoryStore] = None,
        memory_top_k_default: int = 5,
        user_id: Optional[str] = None,
    ) -> None:
        self.default_alias = default_alias
        self.debug = debug
        self.memory_store = memory_store
        self.memory_top_k_default = memory_top_k_default
        # Optional logical user identifier for OpenMemory / other backends.
        self.user_id = user_id

    def respond(self, user_input: str, alias: Optional[str] = None) -> str:
        """Run a single turn through the agent and return the model response.

        This method intentionally stays close to the existing behaviour of the
        CLI and web UI: it resolves the route, builds a prompt, and calls the
        configured LLM endpoint once.
        """
        text = (user_input or "").strip()
        if not text:
            raise ValueError("user_input must be a non-empty string")

        alias_name = (alias or self.default_alias) or self.default_alias

        routing = route(alias_name)
        model_url = routing["model_url"]

        cfg = get_router_alias_config(alias_name)
        memory_enabled = bool(cfg.get("memory_enabled", False))
        memory_top_k = int(cfg.get("memory_top_k", self.memory_top_k_default))

        memory_context: Optional[str] = None
        if memory_enabled and self.memory_store is not None:
            try:
                items = self.memory_store.search(
                    query=text,
                    user_id=self.user_id,
                    alias=alias_name,
                    limit=memory_top_k,
                )
                memory_context = self._format_memory_context(items)
            except Exception as e:  # pragma: no cover - defensive
                if self.debug:
                    print(f"[memory] Failed to query memory: {e}")

        if self.debug:
            print(f"[~] Using alias: {alias_name}")
            print(f"[~] Model URL: {model_url}")
            print("[~] Building prompt…")

        llm_runner = LLMRunner(model_url=model_url)
        prompt = build_prompt(alias_name, text, memory_context=memory_context)

        if self.debug:
            print("[~] Running LLM inference…")

        result = llm_runner.run_chat(prompt)

        # For GPT-OSS / Harmony-formatted responses, strip analysis/channel
        # scaffolding and return only the `final` channel content.
        if cfg.get("format") == "gpt-oss-harmony":
            cleaned = self._extract_gpt_oss_final(result)
            if cleaned:
                result = cleaned

        if memory_enabled and self.memory_store is not None:
            try:
                self.memory_store.add_interaction(
                    user_text=text,
                    assistant_text=result,
                    user_id=self.user_id,
                    alias=alias_name,
                )
            except Exception as e:  # pragma: no cover - defensive
                if self.debug:
                    print(f"[memory] Failed to store interaction: {e}")

        return result

    def _format_memory_context(self, items: List[MemoryItem]) -> Optional[str]:
        """Render retrieved memories into a compact text block for prompts."""
        if not items:
            return None

        lines = []
        for i, item in enumerate(items, start=1):
            prefix = f"[{i}]"
            score_str = f" (score={item.score:.3f})" if isinstance(item.score, (int, float)) else ""
            lines.append(f"{prefix}{score_str} {item.content}")
        return "\n".join(lines)

    def _extract_gpt_oss_final(self, raw: str) -> Optional[str]:
        """Extract the `final` channel content from a Harmony-formatted reply.

        Expected structure (simplified):
        <|channel|>analysis<|message|>...<|end|><|start|>assistant<|channel|>final<|message|>FINAL_TEXT
        """
        if not raw:
            return None

        marker = "<|channel|>final<|message|>"
        idx = raw.rfind(marker)
        if idx == -1:
            return None

        content = raw[idx + len(marker) :]

        # Strip any trailing control tokens if present.
        for stop in ("<|return|>", "<|end|>"):
            stop_idx = content.find(stop)
            if stop_idx != -1:
                content = content[:stop_idx]
                break

        return content.strip() or None
