# main.py

import argparse
import sys

from requests.exceptions import RequestException

from agent import Agent
from tts import speak_text


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
    parser.add_argument(
        "--speak",
        "-s",
        action="store_true",
        help="Also send the model output to the TTS hook.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if not args.text:
        print("[!] No text prompt provided.")
        sys.exit(1)

    agent = Agent(default_alias=args.alias, debug=True)

    try:
        result = agent.respond(args.text, alias=args.alias)
    except RequestException as e:
        print(f"[x] Failed to reach model endpoint: {e}")
        sys.exit(1)

    print("\n[✓] LLM output:\n")
    if result.strip():
        print(result)
    else:
        print("[!] Model returned empty response.")
    print()

    if args.speak:
        if result.strip():
            print("[~] Sending output to TTS…")
            speak_text(result)
        else:
            print("[~] Skipping TTS (no content returned).")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[Shutdown] Terminated by user.")
