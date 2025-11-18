# inference/llm_runner.py

import re
import asyncio
import aiohttp
import json
import requests
from typing import AsyncGenerator

class LLMRunner:
    """
    General-purpose LLM inference runner.

    Takes a fully-formed prompt string and sends it to the configured LLM endpoint.
    Supports both blocking and streaming modes.

    Example:
        llm = LLMRunner(model_url="http://localhost:30105/completion")
        response = llm.run_chat(full_prompt)
    """

    def __init__(
        self,
        model_url: str,
        max_tokens: int = 2048,
        debug: bool = True
    ):
        self.model_url = model_url
        self.max_tokens = max_tokens
        self.debug = debug

    def run_chat(self, full_prompt: str) -> str:
        """
        Sends a full prompt and returns the response as a string.
        """
        response = requests.post(
            self.model_url,
            json={
                "prompt": full_prompt,
                "temperature": 0.8,
                "max_tokens": self.max_tokens,
                "stream": False,
            },
            timeout=60,
        )

        response.raise_for_status()
        data = response.json()

        # Basic sanity check
        result = data.get("content", "")
        # Strip ANSI noise if any
        result = re.sub(
            r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])", "", result
        )
        result = result.replace("\x1b", "").replace("\x00", "").strip()

        return result

    async def run_chat_stream(self, full_prompt: str) -> AsyncGenerator[str, None]:
        """
        Sends a full prompt and yields response chunks as they arrive.
        Assumes the endpoint returns Server-Sent Events-style lines like:
        `data: {"content": "..."}`
        """
        async with aiohttp.ClientSession() as session:
            async with session.post(
                self.model_url,
                json={
                    "prompt": full_prompt,
                    "temperature": 0.8,
                    "max_tokens": self.max_tokens,
                    "stream": True,
                },
                timeout=None,
            ) as resp:
                resp.raise_for_status()

                async for line in resp.content:
                    clean = line.decode("utf-8").strip()
                    if not clean or not clean.startswith("data:"):
                        continue

                    try:
                        data = json.loads(clean.replace("data: ", "", 1))
                        content = data.get("content", "")
                        if content:
                            yield content
                    except json.JSONDecodeError:
                        if self.debug:
                            print("[Stream] Failed to parse line:", clean)

    def stop(self) -> None:
        """
        Placeholder for any cleanup logic if needed.
        """
        pass
