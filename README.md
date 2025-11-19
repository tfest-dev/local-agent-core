# local-agent-core

A lightweight, privacy-focused framework for building small AI agents that run entirely on your own hardware.
This project is designed to be modular, simple to extend, and suitable for self-hosted or offline environments.

## Current Components

### LLM Runner
A clean wrapper around a local or remote LLM HTTP endpoint.

Supports:
- synchronous inference
- streaming responses
- generic JSON/`/completion` style APIs

### Routing Layer
Config-driven routing via `router.yaml` / `router.example.yaml`:

- Map human-friendly aliases (e.g. `general`, `code-python`) to models
- Resolve the correct base URL and `/completion` endpoint
- Carry defaults like `speaker`, `stream`, and `system_prompt`

### Prompt Builder
Model-aware prompt construction based on alias configuration.

Built-in formats:
- `llama-chat` – system/user/assistant header style
- `codellama` / `code` – instruction-style coding prompts
- `phind` – Alpaca/Vicuna-style sections
- `phi4` – `<|system|>/<|user|>/<|assistant|>` format
- `plain` – simple system + user concatenation

## Goals of the Project

- Local-first, privacy-first design
- Minimal dependencies
- Modular architecture (LLM, routing, prompts, tools)
- Clear, maintainable code
- Step-by-step expansion with tested milestones

Next planned modules:
- simple CLI entrypoint
- agent loop and tool hooks
- optional TTS integration
