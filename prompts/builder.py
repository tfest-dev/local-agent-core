# prompts/builder.py

from typing import Callable, Dict
from inference.prompt_router import get_router_alias_config


def _build_llama_chat(system_prompt: str, user_input: str) -> str:
    """
    Llama-style chat formatting with explicit system/user/assistant turns.
    This is suitable for many chat-tuned GGUF models that expect
    meta-style headers.
    """
    return (
        "<s><|start_header_id|>system<|end_header_id|>\n\n"
        f"{system_prompt}"
        "<|eot_id|><|start_header_id|>user<|end_header_id|>\n\n"
        f"{user_input}"
        "<|eot_id|><|start_header_id|>assistant<|end_header_id|>\n"
    )


def _build_codellama(system_prompt: str, user_input: str) -> str:
    """
    CodeLlama-style instruction prompt.

    Common pattern:
    [INST] <<SYS>> system_prompt <</SYS>>

    user_input

    [/INST]
    """
    return (
        "[INST] <<SYS>> "
        f"{system_prompt}"
        " <</SYS>>\n\n"
        f"{user_input}\n"
        "[/INST]"
    )


def _build_phind(system_prompt: str, user_input: str) -> str:
    """
    Phind-style prompt with explicit sections, aligned with the
    Alpaca/Vicuna-style instruction format they document.
    """
    return (
        f"### System Prompt\n{system_prompt}\n\n"
        f"### User Message\n{user_input}\n\n"
        "### Assistant\n"
    )


def _build_phi4(system_prompt: str, user_input: str) -> str:
    """
    Phi-4 mini instruct format:

    <|system|>System message<|end|><|user|>User message<|end|><|assistant|>
    """
    return (
        f"<|system|>{system_prompt}<|end|>"
        f"<|user|>{user_input}<|end|>"
        "<|assistant|>"
    )


def _build_plain(system_prompt: str, user_input: str) -> str:
    """
    Simple 'system + user' concatenation for generic models.
    """
    return f"System: {system_prompt}\n\nUser: {user_input}\nAssistant:"


FORMAT_BUILDERS: Dict[str, Callable[[str, str], str]] = {
    "llama-chat": _build_llama_chat,
    "codellama": _build_codellama,
    "code": _build_codellama,
    "phind": _build_phind,
    "phi4": _build_phi4,
    "plain": _build_plain,
}


def build_prompt(alias: str, user_input: str) -> str:
    """
    Builds a prompt string using the system prompt and format defined in the router
    configuration for the given alias and user input.

    - Reads alias config via prompt_router
    - Uses 'format' from the alias (defaults to 'llama-chat')
    - Falls back to a sensible system prompt if not provided
    """
    cfg = get_router_alias_config(alias)

    system_prompt = cfg.get(
        "system_prompt",
        "You are an AI assistant."
    )

    format_name = cfg.get("format", "llama-chat")
    builder = FORMAT_BUILDERS.get(format_name)

    if builder is None:
        raise ValueError(f"Unknown prompt format: {format_name}")

    return builder(system_prompt, user_input)
