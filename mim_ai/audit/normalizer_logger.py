"""
Normalizer feedback-loop logger.

Purpose: let developers see, in production, WHICH custom jargon
actually fires and WHICH OOV Latin tokens keep showing up. Use it
weekly to refine your `darija/arabizi.yaml` dictionary:

    SELECT jargon_skipped FROM normalizer_events
    WHERE ts > datetime('now', '-7 days');

The returned {token: count} maps tell you exactly what to add.

⚠️  This log CAN contain user tokens (the OOV samples). It is NOT
a compliance trail. Configure `capture_skipped_tokens=False` in
production if user text is sensitive.
"""
from __future__ import annotations

import json
import random
from datetime import datetime, timezone

from .backends import create_backend
from .config import NormalizerLogConfig


class NormalizerLogger:
    def __init__(self, config: NormalizerLogConfig) -> None:
        self.config = config
        self.enabled = config.enabled

        if not self.enabled:
            return

        self._backend = create_backend(config, getattr(config, "collection", "normalizer_events"))

        if config.purge_on_start:
            self._backend.purge_older_than(config.retention_days)

    # -----------------------------------------------------------------
    def emit(
        self,
        *,
        trace_id: str,
        user_ref: str | None = None,
        lang_detected: str | None = None,
        code_switched: bool = False,
        jargon_used: dict[str, int] | None = None,
        jargon_skipped: dict[str, int] | None = None,
        arabizi_used: int = 0,
        arabizi_oov: int = 0,
        rules_applied: int = 0,
        urls_protected: int = 0,
        duration_ms: int | None = None,
    ) -> None:
        """
        Write one normalizer event.

        `jargon_used`      : {custom_dict_key: count} that matched.
        `jargon_skipped`   : {token: count} that missed every lookup —
                             these are dictionary candidates.
        """
        if not self.enabled:
            return

        # Sampling — drop events probabilistically on high-traffic apps.
        if self.config.sample_rate < 1.0:
            if random.random() > self.config.sample_rate:
                return

        used = dict(jargon_used or {}) if self.config.capture_jargon_used else {}
        skipped = dict(jargon_skipped or {}) if self.config.capture_jargon_skipped else {}

        # If the dev opts out of raw tokens, keep counts only.
        if not self.config.capture_skipped_tokens and skipped:
            skipped = {"<count>": sum(skipped.values())}

        # Hard cap so a pathological input can't blow up storage.
        cap = self.config.max_tokens_per_event
        if len(skipped) > cap:
            skipped = dict(list(skipped.items())[:cap])

        row = {
            "ts":             datetime.now(timezone.utc).isoformat(),
            "trace_id":       trace_id,
            "user_ref":       user_ref,
            "lang_detected":  lang_detected,
            "code_switched":  int(code_switched),
            "jargon_used":    json.dumps(used,    ensure_ascii=False),
            "jargon_skipped": json.dumps(skipped, ensure_ascii=False),
            "arabizi_used":   arabizi_used,
            "arabizi_oov":    arabizi_oov,
            "rules_applied":  rules_applied,
            "urls_protected": urls_protected,
            "duration_ms":    duration_ms,
        }
        self._backend.append(row)

    def purge_expired(self) -> int:
        if not self.enabled:
            return 0
        return self._backend.purge_older_than(self.config.retention_days)