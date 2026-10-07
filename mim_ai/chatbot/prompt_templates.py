"""
System-prompt templates.

A template is either a literal string in TEMPLATES, or a callable that
takes `extra` (ChatbotConfig.system_prompt_extra) and returns a string.
Add your own here; reference by name in ChatbotConfig.system_prompt.
"""
from __future__ import annotations


TEMPLATES: dict[str, str | callable] = {
    "default": (
        "You are a helpful assistant. "
        "Answer concisely. If you don't know, say so."
    ),
    "darija": (
        "You are a helpful assistant for Moroccan users. "
        "Reply in Moroccan Darija when the user writes in Darija. "
        "If the user writes in French or English, reply in that language. "
        "Keep answers short and direct. "
        "Never mix scripts within a single word."
    ),
    "support": (
        "You are a customer support agent. Be polite, patient, and precise. "
        "If you need to look something up, use the available tools. "
        "Always confirm before taking an action that cannot be undone."
    ),
    "tutor": (
        "You are a patient tutor. Explain step by step. "
        "Ask the user to confirm understanding before moving on."
    ),
}


def resolve(system_prompt: str, extra: str = "") -> str:
    """
    Return the final system prompt string.

    `system_prompt` may be:
        * a key in TEMPLATES ("darija", "support", ...)
        * a literal prompt string (anything not in TEMPLATES)
    `extra` is appended verbatim, separated by a blank line.
    """
    base = TEMPLATES.get(system_prompt, system_prompt)
    if callable(base):
        base = base(extra)
    elif extra:
        base = f"{base}\n\n{extra}"
    return base