# local-agent-core

A lightweight, privacy-focused framework for building small AI agents that run entirely on your own hardware.
This project is designed to be modular, simple to extend, and suitable for self-hosted or offline environments.

## Current Components

### LLM Runner
A clean wrapper around a local or remote LLM endpoint.
Supports:
- synchronous inference
- streaming responses
- generic JSON API endpoints

This is the core building block for later agent logic.

## Goals of the Project
- Local-first, privacy-first design
- Minimal dependencies
- Modular architecture (LLM, routing, prompts, tools)
- Clear, maintainable code
- Step-by-step expansion with tested milestones

Additional modules (prompt routing, agent loop, TTS hooks) will be added incrementally.
