# tts/print_tts.py

def speak_text(text: str) -> None:
    """
    Placeholder TTS implementation.

    In a real deployment, this function can be replaced or extended
    with a concrete engine (e.g. edge-tts, ElevenLabs, local TTS).
    For now, it just logs the text to stdout to demonstrate the hook.
    """
    # In a real implementation, this might play audio instead.
    print("[TTS] Speaking text:")
    print(text)
    print()
