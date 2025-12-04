# local-agent-core

![Local Agent Core UI](docs/images/flask-webui-basic.png)

*A minimal web UI included with the project. Branding, colours and layout are intended to be customised per client.*

A lightweight, privacy-focused framework for building small AI agents that run entirely on your own hardware. This project is designed to be modular, simple to extend, and suitable for self-hosted or offline environments.

## Dependencies
- [OpenMemory](https://github.com/CaviraOSS/OpenMemory) — provides long‑term memory for AI systems. Self‑hosted. Local‑first. Explainable. Scalable. A full cognitive memory engine — not a vector database.

## Environment configuration

Runtime configuration is provided via environment variables (optionally loaded from a `.env` file using shell tooling):

- `LAC_WEB_HOST` – bind address for the Flask web UI (default: `0.0.0.0`).
- `LAC_WEB_PORT` – port for the web UI (default: `5001`).
- `OPENMEMORY_URL` / `OM_BASE_URL` – base URL for the OpenMemory backend (default: `http://localhost:8080`).
- `OPENMEMORY_API_KEY` / `OM_API_KEY` – optional API key for authenticated OpenMemory instances.

See `.env.example` for a template and `.env` for a sample local dev setup.

## Current Components

### Agent & Orchestrator
A shared `Agent` abstraction (used by both CLI and web UI) that:

- wraps routing, prompt construction, inference, and memory
- supports a single-model, multi-role pipeline (Interpreter/Planner + Narrator) for GPT‑OSS aliases via an "orchestrator" mode
- threads OpenMemory context and metadata (domains, channels, session kinds) through each turn

### LLM Runner
A clean wrapper around a local or remote LLM HTTP endpoint.

Supports:
- synchronous inference
- streaming responses
- generic JSON `/completion` style APIs

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
- `gpt-oss-harmony` – Harmony prompt format for OpenAI GPT‑OSS models, used by the GPT‑OSS orchestrator for interpreter + narrator phases

### Memory & OpenMemory Integration

- Optional `MemoryStore` abstraction, with `OpenMemoryStore` providing HTTP integration to a self-hosted OpenMemory backend.
- Per-alias controls to enable memory and tune recall depth.
- Retrieved memories are injected as a compact "Relevant past context" block, including domain/channel/session tags.
- Stored interactions are enriched with metadata and tags so the OpenMemory dashboard can distinguish professional vs social, interactive vs automation, and new vs continuation turns.

### TTS Hook (Optional)
A simple text-to-speech hook is provided via `tts.speak_text`.

By default, this just logs the text that would be spoken. In a real deployment, this function can be swapped or extended to use a concrete TTS engine (e.g. edge-tts, ElevenLabs, local speech synthesis).

### Web UI (Optional)
A minimal Flask-based web interface for interacting with the agent:

- Chat-style interface
- Route alias selection (e.g. `gpt-oss` as default, `llama`, `code-python`)
- Professional / Social memory profile toggle for GPT‑OSS, mapping to `gpt-oss` (professional) and `gpt-oss-social` (social) aliases while sharing the same model backend
- Clear branding placeholders so client-specific themes can be applied

## n8n Integration

An example n8n workflow is included under `examples/n8n/local-agent-webhook.json`.

It exposes a HTTP webhook (`/local-agent`) that:
- accepts `{"text": "..."}` as input
- forwards the request to the local `/chat` endpoint
- returns the LLM response as either text or JSON

---

## Goals of the Project
- Local-first, privacy-first design
- Minimal and transparent dependencies
- Modular architecture (LLM runner, routing, prompts, tools, TTS)
- Single-model, multi-role orchestration with long-term memory
- Professional / social personality tracks backed by tagged memory
- Clear, maintainable code
- Step-by-step expansion with tested milestones

---

## Status
- CLI and web UI both use a shared `Agent` abstraction.
- Long-term memory is fully integrated via OpenMemory, with per-alias opt-in and confirmed end-to-end wiring (including API key auth).
- Memory entries are tagged with `memory_domain` (e.g. professional vs social), `channel` (interactive vs automation), and `session_kind` metadata, and key fields are projected to OpenMemory `tags` for visibility in the dashboard.
- Web UI exposes GPT‑OSS as the default route with a professional/social profile switch that maps to `gpt-oss` and `gpt-oss-social` aliases.
- GPT‑OSS / Harmony prompt format is supported via the `gpt-oss-harmony` builder, including a two-pass Interpreter/Planner + Narrator orchestrator for GPT‑OSS aliases.
- A global inference lock in `LLMRunner` serialises all LLM calls (CLI, web UI, automation), providing simple queueing semantics for a single-GPU deployment.
- Interpreter output is parsed into a structured `InterpreterResult` and a skeleton `ToolPlan` is derived for future tool execution, but no tools are executed yet.
- All existing modules are fully functional and tested independently. Each commit represents a clean, working milestone that can be extended safely.

## Next Planned Modules
- **Tool/action layer**
  - Tool interface + registry
  - Executor that uses `ToolPlan` and simple policies (e.g. execute only
    for automation channels)
- **Optional background task runner** for scheduled or long-running actions
- **Speech input (STT)** integration for voice-driven interactions
- **Expanded TTS** integration surfaced in the web UI

---
