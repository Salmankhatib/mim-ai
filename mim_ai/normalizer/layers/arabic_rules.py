"""
Arabic-script orthography rules for Layer 2.

Only rules that are *safe for both MSA and Darija* live here.
Character tables are plain dicts so they can be overridden from
`data/arabic_rules.yaml` without touching code.
"""
from __future__ import annotations

import re

ALEF_FORMS  = {"أ": "ا", "إ": "ا", "آ": "ا", "ٱ": "ا"}
YA_FORMS    = {"ى": "ي"}
TA_MARBUTA  = {"ة": "ه"}
ARABIC_INDIC_DIGITS = {
    "٠": "0", "١": "1", "٢": "2", "٣": "3", "٤": "4",
    "٥": "5", "٦": "6", "٧": "7", "٨": "8", "٩": "9",
}
TASHKEEL_RE = re.compile(r"[\u064B-\u065F\u0670]")


def unify_alef(token: str) -> str:
    return "".join(ALEF_FORMS.get(c, c) for c in token)


def unify_ya(token: str) -> str:
    return "".join(YA_FORMS.get(c, c) for c in token)


def unify_ta_marbuta(token: str) -> str:
    return "".join(TA_MARBUTA.get(c, c) for c in token)


def remove_tashkeel(token: str) -> str:
    return TASHKEEL_RE.sub("", token)


def normalize_digits(token: str) -> str:
    return "".join(ARABIC_INDIC_DIGITS.get(c, c) for c in token)