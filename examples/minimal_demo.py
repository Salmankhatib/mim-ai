"""Minimal demo app for MIM.

Run from the project root:
    python examples/minimal_demo.py

It loads the default config, normalizes a sample Darija sentence, and only
tries a live chatbot call if the configured LLM API key is present.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mim_ai import Mim


def main() -> None:
    config_path = os.environ.get("MIM_CONFIG", "mimExemple.yaml")
    app = Mim.from_config(config_path)

    sample = "salam wa7ed 3la ekher, bghit n3ref kifach nt3amro app?"
    if app.config.normalizer.enabled:
        cleaned = app.normalizer.normalize(sample)
        print("Normalized Darija:")
        print(cleaned)

    key_name = app.config.chatbot.llm_api_key_env
    if app.config.chatbot.enabled and os.getenv(key_name):
        reply = app.chat("salam, chkoun nta?", session_id="demo-session")
        print("\nChatbot reply:")
        print(reply.text)
    else:
        print(f"\nChatbot demo skipped: set {key_name} to test the live chat path.")

    if app.config.voice.enabled:
        print("\nVoice pipeline is enabled in the config and ready for microphone input.")


if __name__ == "__main__":
    main()
