# prompts/builder.py

from typing import Callable, Dict, Optional
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


def _build_gpt_oss_harmony(system_prompt: str, user_input: str) -> str:
    """Build a Harmony-formatted prompt for gpt-oss models.

    This follows the guidance from the harmony docs:
    - A fixed system message describing identity, dates, and reasoning level.
    - A developer message that carries our existing `system_prompt` as
      instructions.
    - A user message with the raw input.
    - An open assistant message to continue generation.
    """
    from datetime import date

    today = date.today().isoformat()

    system_block = (
        "<|start|>system<|message|>"
        "You are ChatGPT, a large language model trained by OpenAI.\n"
        "Knowledge cutoff: 2024-06\n"
        f"Current date: {today}\n\n"
        "Reasoning: medium\n\n"
        "# Valid channels: analysis, commentary, final. Channel must be included for every message.<|end|>"
    )

    developer_block = (
        "<|start|>developer<|message|># Instructions\n\n"
        f"{system_prompt}<|end|>"
    )

    user_block = (
        "<|start|>user<|message|>"
        f"{user_input}<|end|>"
    )

    assistant_start = "<|start|>assistant"

    return system_block + developer_block + user_block + assistant_start


FORMAT_BUILDERS: Dict[str, Callable[[str, str], str]] = {
    "llama-chat": _build_llama_chat,
    "codellama": _build_codellama,
    "code": _build_codellama,
    "phind": _build_phind,
    "phi4": _build_phi4,
    "plain": _build_plain,
    # Harmony / gpt-oss format as described in docs/external/harmony-*.md
    "gpt-oss-harmony": _build_gpt_oss_harmony,
}


def build_prompt(alias: str, user_input: str, memory_context: Optional[str] = None) -> str:
    """Build a prompt string using router config for the given alias.

    `memory_context`, when provided, is injected ahead of the raw user input as
    a "Relevant past context" section so all format builders can remain
    unchanged.
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

    if memory_context:
        decorated_user_input = (
            "Relevant past context:\n"
            f"{memory_context}\n\n"
            "Current input:\n"
            f"{user_input}"
        )
    else:
        decorated_user_input = user_input

    return builder(system_prompt, decorated_user_input)
