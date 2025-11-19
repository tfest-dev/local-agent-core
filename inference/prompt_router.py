# inference/prompt_router.py

from pathlib import Path
from typing import Dict, Any
import yaml

PROJECT_ROOT = Path(__file__).parent.parent

def _load_router_config() -> Dict[str, Any]:
    """
    Load router configuration from router.yaml (if present),
    otherwise fall back to router.example.yaml.
    """
    candidates = [
        PROJECT_ROOT / "router.yaml",
        PROJECT_ROOT / "router.example.yaml",
    ]

    for path in candidates:
        if path.exists():
            with open(path, "r") as f:
                return yaml.safe_load(f)

    raise FileNotFoundError(
        "No router configuration found. "
        "Create router.yaml based on router.example.yaml."
    )

ROUTER_CONFIG = _load_router_config()


def get_router_alias_config(alias: str) -> Dict[str, Any]:
    """
    Returns the merged configuration dict for a given alias.
    Falls back to defaults if alias not found.
    """
    defaults = ROUTER_CONFIG.get("defaults", {})

    alias_config = ROUTER_CONFIG.get("aliases", {}).get(alias, {})
    merged = {**defaults, **alias_config}

    if "model" not in merged:
        raise KeyError(f"Alias '{alias}' does not define or inherit a 'model' key.")

    return merged


def get_model_url(model_key: str) -> str:
    """
    Returns the URL for the given model key.
    Raises KeyError if model is undefined.
    Appends /completion if not present.
    """
    models = ROUTER_CONFIG.get("models", {})
    model_conf = models.get(model_key)
    if not model_conf:
        raise KeyError(f"Model key '{model_key}' not found in router config.")

    url = model_conf["url"]
    if not url.endswith("/completion"):
        url += "/completion"
    return url


def route(alias: str) -> Dict[str, Any]:
    """
    Given an alias, returns a routing configuration dict including:
    - model_url
    - speaker
    - stream
    - system_prompt (optional, falls back to defaults)
    """
    alias_conf = get_router_alias_config(alias)
    model_key = alias_conf["model"]
    model_url = get_model_url(model_key)

    return {
        "model_url": model_url,
        "speaker": alias_conf.get("speaker", "default"),
        "stream": alias_conf.get("stream", False),
        "system_prompt": alias_conf.get(
            "system_prompt",
            ROUTER_CONFIG.get("defaults", {}).get("system_prompt", "")
        ),
    }
