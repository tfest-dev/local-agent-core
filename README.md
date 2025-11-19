# local-agent-core

![Local Agent Core UI](docs/images/flask-webui-basic.png)

*A minimal web UI included with the project. Branding, colours and layout are intended to be customised per client.*


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

- map human-friendly aliases (e.g. `general`, `code-python`) to models
- resolve the correct base URL and `/completion` endpoint
- carry defaults like `speaker`, `stream`, and `system_prompt`

### Prompt Builder
Model-aware prompt construction based on alias configuration.

Built-in formats:
- `llama-chat` – system/user/assistant header style
- `codellama` / `code` – instruction-style coding prompts
- `phind` – Alpaca/Vicuna-style sections
- `phi4` – `<|system|>/<|user|>/<|assistant|>` format
- `plain` – simple system + user concatenation

### TTS Hook (Optional)
A simple text-to-speech hook is provided via `tts.speak_text`.

By default, this just logs the text that would be spoken. In a real deployment,
this function can be swapped or extended to use a concrete TTS engine
(e.g. edge-tts, ElevenLabs, local speech synthesis).

### Web UI (Optional)
A minimal Flask-based web interface for interacting with the agent:

- Chat-style interface
- Route alias selection
- Clear branding placeholders so client-specific themes can be applied

---

## Goals of the Project
- Local-first, privacy-first design
- Minimal and transparent dependencies
- Modular architecture (LLM runner, routing, prompts, tools, TTS)
- Clear, maintainable code
- Step-by-step expansion with tested milestones

---

## Next Planned Modules
- **Agent loop** + simple tool/action hooks
- **Local memory integration** (YAML/JSON or SQLite)
- **Optional background task runner** for scheduled or long-running actions

---

## Status
All existing modules are fully functional and tested independently.
Each commit represents a clean, working milestone that can be extended safely.
