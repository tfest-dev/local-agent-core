# agent/core.py

from typing import Optional

from inference import LLMRunner, route
from prompts import build_prompt


class Agent:
    """Core agent abstraction for local-agent-core.

    This wraps routing, prompt construction, and LLM invocation behind a
    simple `respond` method so frontends (CLI, web UI, future voice UI)
    all share the same request flow.
    """

    def __init__(self, default_alias: str = "general", debug: bool = True) -> None:
        self.default_alias = default_alias
        self.debug = debug

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

        if self.debug:
            print(f"[~] Using alias: {alias_name}")
            print(f"[~] Model URL: {model_url}")
            print("[~] Building prompt…")

        llm_runner = LLMRunner(model_url=model_url)
        prompt = build_prompt(alias_name, text)

        if self.debug:
            print("[~] Running LLM inference…")

        result = llm_runner.run_chat(prompt)
        return result
