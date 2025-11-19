# main.py

import argparse
import sys

from requests.exceptions import RequestException

from inference import LLMRunner, route
from prompts import build_prompt


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a local-agent-core prompt against a configured model alias."
    )
    parser.add_argument(
        "--alias",
        "-a",
        default="general",
        help="Router alias to use (e.g. 'general', 'code-python').",
    )
    parser.add_argument(
        "--text",
        "-t",
        required=True,
        help="User input text to send to the model.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if not args.text:
        print("[!] No text prompt provided.")
        sys.exit(1)

    routing = route(args.alias)
    model_url = routing["model_url"]

    print(f"[~] Using alias: {args.alias}")
    print(f"[~] Model URL: {model_url}")

    llm_runner = LLMRunner(model_url=model_url)

    print("[~] Building prompt…")
    prompt = build_prompt(args.alias, args.text)

    print("[~] Running LLM inference…")
    try:
        result = llm_runner.run_chat(prompt)
    except RequestException as e:
        print(f"[x] Failed to reach model endpoint: {e}")
        sys.exit(1)

    print("\n[✓] LLM output:\n")
    print(result)
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[Shutdown] Terminated by user.")
