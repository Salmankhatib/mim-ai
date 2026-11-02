"""Shared regular expressions for Moroccan identity and phone formats."""

CIN_MA_REGEX = r"\b[A-Z]{1,2}\d{5,6}\b"
PHONE_MA_REGEX = r"(?<!\d)(?:\+212|0)[2567]\d{8}(?!\d)"

__all__ = ["CIN_MA_REGEX", "PHONE_MA_REGEX"]
