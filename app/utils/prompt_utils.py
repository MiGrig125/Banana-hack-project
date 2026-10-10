"""Helpers for prompt cleaning and simple intent keywords."""

import re
from typing import List


def clean_prompt(text: str) -> str:
    """Strip and normalize whitespace in a user prompt."""
    if not text:
        return ""
    return re.sub(r"\s+", " ", text.strip())


def contains_any(text: str, keywords: List[str]) -> bool:
    """Case-insensitive keyword check."""
    lower = text.lower()
    return any(kw.lower() in lower for kw in keywords)
