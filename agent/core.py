# agent/core.py

from collections import deque
from dataclasses import dataclass
from typing import Deque, Dict, Optional, List, Tuple

from inference import LLMRunner, route, get_router_alias_config
from prompts import build_prompt
from memory import MemoryStore, MemoryItem
from tools import ToolExecutor


@dataclass
class InterpreterResult:
    """Structured view of the interpreter/planner output.

    Parsed from the first LLM pass in orchestrator mode so that downstream
    code (tools, policies) can use a stable structure instead of
    re-interpreting free-form text.
    """

    intent: str = ""
    category: str = ""
    needs_tools: bool = False
    tools_hint: str = ""
    thread: str = ""  # "new" or "continuation" when available
    summary: str = ""
    raw_text: str = ""  # original interpreter text for debugging


@dataclass
class ToolPlan:
    """Lightweight skeleton for future tool/executor integration.

    Currently derived from the interpreter classification only; no tools
    are executed yet.
    """

    needs_tools: bool = False
    categories: List[str] = None
    reason: str = ""  # short note from interpreter / planner


@dataclass
class TurnState:
    """State container shared across orchestrator phases for a single turn."""

    text: str
    alias_name: str
    memory_context: Optional[str]
    interpreter_raw: str = ""
    interpreter: Optional[InterpreterResult] = None
    tool_plan: Optional[ToolPlan] = None


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
        memory_domain: str = "professional",
        recent_history_window: int = 5,
    ) -> None:
        self.default_alias = default_alias
        self.debug = debug
        self.memory_store = memory_store
        self.memory_top_k_default = memory_top_k_default
        # Optional logical user identifier for OpenMemory / other backends.
        self.user_id = user_id
        # Logical memory domain for this agent instance (e.g. "professional"
        # vs "social"). This is used purely for tagging / routing in memory
        # backends and does not affect core inference.
        self.memory_domain = memory_domain
        # Per-(user, alias) window of recent user inputs, used for lightweight
        # continuity / branching heuristics and tagging.
        self._recent_history_window = max(1, recent_history_window)
        self._recent_user_inputs: Dict[Tuple[str, str], Deque[str]] = {}

    def respond(self, user_input: str, alias: Optional[str] = None, *, channel: str = "interactive") -> str:
        """Run a single turn through the agent and return the model response.

        For simple aliases, this is a single LLM call. When an alias is marked
        as `orchestrator` in the router config, this instead runs a small
        multi-role pipeline (Interpreter/Planner + Narrator) using the same
        underlying model endpoint.
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
        memory_domain_cfg = cfg.get("memory_domain")
        effective_domain = str(memory_domain_cfg or self.memory_domain)
        orchestrator_enabled = bool(cfg.get("orchestrator", False))

        # Lightweight continuity tagging: track the last few user inputs per
        # (user_id, alias) key so we can distinguish new queries from
        # continuations of an in-progress thread. For now we record this in
        # metadata rather than altering routing logic.
        user_key = self.user_id or "default"
        history_key = (user_key, alias_name)
        history = self._recent_user_inputs.get(history_key)
        if history is None:
            history = deque(maxlen=self._recent_history_window)
            self._recent_user_inputs[history_key] = history

        session_kind = "automation" if channel != "interactive" else (
            "continuation" if history else "new"
        )

        # Record this input for future turns.
        history.append(text)

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

        # Orchestrated multi-role pipeline: Interpreter/Planner + Narrator.
        if orchestrator_enabled:
            result = self._respond_orchestrated(
                text=text,
                alias_name=alias_name,
                llm_runner=llm_runner,
                cfg=cfg,
                memory_context=memory_context,
                channel=channel,
            )
        else:
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
                extra_metadata = {
                    "memory_domain": effective_domain,
                    "channel": channel,
                    "session_kind": session_kind,
                    # Give OpenMemory some lightweight short-term context so
                    # downstream analysis can distinguish branches vs
                    # continuations without needing a separate store.
                    "recent_user_inputs": list(history),
                }
                self.memory_store.add_interaction(
                    user_text=text,
                    assistant_text=result,
                    user_id=self.user_id,
                    alias=alias_name,
                    extra_metadata=extra_metadata,
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

            # Surface key metadata tags inline so the model can distinguish
            # between different memory domains / channels without needing
            # separate stores.
            domain = item.metadata.get("memory_domain") if isinstance(item.metadata, dict) else None
            channel = item.metadata.get("channel") if isinstance(item.metadata, dict) else None
            session_kind = item.metadata.get("session_kind") if isinstance(item.metadata, dict) else None

            tags = []
            if domain:
                tags.append(str(domain))
            if channel:
                tags.append(str(channel))
            if session_kind:
                tags.append(str(session_kind))

            tag_str = f" [{' | '.join(tags)}]" if tags else ""

            lines.append(f"{prefix}{score_str}{tag_str} {item.content}")
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

    # ------------------------------------------------------------------
    # Orchestrator helpers
    # ------------------------------------------------------------------

    def _parse_interpreter_output(self, text: str) -> InterpreterResult:
        """Parse labelled interpreter output into an InterpreterResult.

        Expected format (all labels optional but recommended):

            Intent: ...
            Category: ...
            Needs_tools: yes/no ...
            Thread: new/continuation
            Summary: ...
        """
        result = InterpreterResult(raw_text=(text or "").strip())
        if not text:
            return result

        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line or ":" not in line:
                continue
            label, value = line.split(":", 1)
            label = label.strip().lower()
            value = value.strip()

            if label == "intent":
                result.intent = value
            elif label == "category":
                result.category = value
            elif label == "needs_tools":
                lowered = value.lower()
                result.needs_tools = lowered.startswith("y") or "true" in lowered
                # keep any free-form hint about which tools in tools_hint
                result.tools_hint = value
            elif label == "thread":
                result.thread = value
            elif label == "summary":
                result.summary = value

        return result

    def _derive_tool_plan(self, interp: InterpreterResult) -> ToolPlan:
        """Derive a minimal ToolPlan from interpreter classification.

        This does not execute tools; it just records intent so that a
        future executor layer can act on it.
        """
        plan = ToolPlan(needs_tools=interp.needs_tools, categories=[], reason=interp.summary)

        hint = (interp.tools_hint or "").lower()
        cats: List[str] = []
        if any(w in hint for w in ("email", "smtp", "sendgrid", "ses", "mail")):
            cats.append("email")
        if any(w in hint for w in ("workflow", "airflow", "prefect", "dag")):
            cats.append("workflow")
        if any(w in hint for w in ("file", "filesystem", "disk")):
            cats.append("filesystem")
        if any(w in hint for w in ("http", "api", "request", "webhook")):
            cats.append("http")
        if any(w in hint for w in ("note", "notes", "obsidian", "journal")):
            cats.append("notes")

        plan.categories = cats
        return plan

    def _respond_orchestrated(
        self,
        *,
        text: str,
        alias_name: str,
        llm_runner: LLMRunner,
        cfg: dict,
        memory_context: Optional[str],
        channel: str,
    ) -> str:
        """Multi-role pipeline using a single model endpoint.

        Phase 1: Interpreter/Planner – classify the request and produce a
        compact analysis.
        Phase 2: Narrator – turn that analysis + context into the final
        user-facing answer.

        Tools are not yet invoked here; this is purely reasoning + narration.
        """
        # --- Phase 1: Interpreter / Planner ---
        interpreter_instructions = (
            "You are the interpreter and planner for this agent. Given the user's "
            "latest input and any relevant past context, produce a SHORT, "
            "readable classification using the following exact fields:\n\n"
            "Intent: <one-line description of what the user wants>\n"
            "Category: <high-level area, e.g. planning / coding / research / ops>\n"
            "Needs_tools: <yes/no and which kinds if yes>\n"
            "Thread: <new/continuation>\n"
            "Summary: <2-3 short sentences with key details for execution>\n\n"
            "Write plain text with these labels exactly, no JSON, no bullet "
            "lists, no markdown headings."
        )

        # Shared state object for this turn across phases.
        state = TurnState(
            text=text,
            alias_name=alias_name,
            memory_context=memory_context,
        )

        if memory_context:
            interp_user = (
                f"{interpreter_instructions}\n\n"
                "--- RELEVANT PAST CONTEXT ---\n"
                f"{memory_context}\n\n"
                "--- CURRENT USER INPUT ---\n"
                f"{text}"
            )
        else:
            interp_user = (
                f"{interpreter_instructions}\n\n"
                "--- CURRENT USER INPUT ---\n"
                f"{text}"
            )

        # We pass `memory_context=None` here because it has already been
        # embedded into the interpreter input where relevant.
        interp_prompt = build_prompt(alias_name, interp_user, memory_context=None)

        if self.debug:
            print("[orchestrator] Running Interpreter/Planner phase…")

        interp_raw = llm_runner.run_chat(interp_prompt)
        if cfg.get("format") == "gpt-oss-harmony":
            cleaned = self._extract_gpt_oss_final(interp_raw)
            if cleaned:
                interp_raw = cleaned

        state.interpreter_raw = (interp_raw or "").strip()
        state.interpreter = self._parse_interpreter_output(state.interpreter_raw)
        state.tool_plan = self._derive_tool_plan(state.interpreter)

        executor = ToolExecutor()
        interactive_allowed = cfg.get("interactive_tool_categories") or []
        tool_results = executor.execute(
            state.tool_plan,
            state,
            channel=channel,
            interactive_allowed=interactive_allowed,
        )

        if self.debug:
            print("[orchestrator] Interpreter classification:\n" + str(state.interpreter_raw))
            if state.tool_plan and state.tool_plan.needs_tools:
                print("[orchestrator] Tool plan (skeleton): ", state.tool_plan)
            if tool_results:
                print("[orchestrator] Tool results (may be planning-only):")
                for res in tool_results:
                    print("  -", res)

        # --- Phase 2: Narrator ---
        narrator_instructions = (
            "You are the narrator for this agent. Your job is to turn the "
            "interpreter's internal analysis into a clear, concise response for "
            "the user. Use the analysis only as internal guidance.\n\n"
            "You are given:\n"
            "- The latest user input.\n"
            "- Any relevant past context.\n"
            "- The interpreter's analysis.\n\n"
            "Write the final answer to the user. Do NOT include the "
            "interpreter analysis itself; only return the answer the user "
            "should see."
        )

        # Include tool plan / results as internal guidance for the narrator
        # without changing user-facing behaviour.
        tool_info_lines: List[str] = []
        if state.tool_plan and state.tool_plan.needs_tools:
            cats = ", ".join(state.tool_plan.categories or [])
            tool_info_lines.append("--- TOOL PLAN (INTERNAL) ---")
            tool_info_lines.append(f"Needs_tools: yes")
            if cats:
                tool_info_lines.append(f"Categories: {cats}")
            if state.tool_plan.reason:
                tool_info_lines.append(f"Reason: {state.tool_plan.reason}")
        if tool_results:
            tool_info_lines.append("--- TOOL RESULTS (INTERNAL) ---")
            for r in tool_results:
                tool_info_lines.append(f"{r.tool_name}: {r.summary}")

        tool_block = ""
        if tool_info_lines:
            tool_block = "\n" + "\n".join(tool_info_lines)

        if memory_context:
            narr_user = (
                f"{narrator_instructions}\n\n"
                "--- RELEVANT PAST CONTEXT ---\n"
                f"{memory_context}\n\n"
                "--- USER INPUT ---\n"
                f"{text}\n\n"
                "--- INTERPRETER ANALYSIS (INTERNAL) ---\n"
                f"{interp_raw}" + tool_block
            )
        else:
            narr_user = (
                f"{narrator_instructions}\n\n"
                "--- USER INPUT ---\n"
                f"{text}\n\n"
                "--- INTERPRETER ANALYSIS (INTERNAL) ---\n"
                f"{interp_raw}" + tool_block
            )

        narr_prompt = build_prompt(alias_name, narr_user, memory_context=None)

        if self.debug:
            print("[orchestrator] Running Narrator phase…")

        narr_raw = llm_runner.run_chat(narr_prompt)
        if cfg.get("format") == "gpt-oss-harmony":
            cleaned = self._extract_gpt_oss_final(narr_raw)
            if cleaned:
                narr_raw = cleaned

        return (narr_raw or "").strip()
