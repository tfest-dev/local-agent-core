# env_loader.py

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional


def load_env(path: Optional[str] = None) -> None:
    """Load key=value pairs from a .env-style file into os.environ.

    - Lines starting with '#' or empty lines are ignored.
    - The first '=' splits key and value.
    - Existing os.environ keys are not overwritten.
    """
    if path is None:
        path = ".env"

    env_path = Path(path)
    if not env_path.is_file():
        return

    try:
        content = env_path.read_text(encoding="utf-8")
    except OSError:
        return

    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key:
            continue
        if key in os.environ:
            continue
        os.environ[key] = value
