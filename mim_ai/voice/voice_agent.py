"""Backward-compatible voice agent shim.

This module used to be an empty placeholder. Keep a tiny compatibility alias so
older imports continue to resolve without changing the real implementation.
"""

from .pipeline import VoicePipeline, VoiceReply


class VoiceAgent(VoicePipeline):
    """Compatibility alias for the main voice pipeline."""

    pass


__all__ = ["VoiceAgent", "VoicePipeline", "VoiceReply"]
