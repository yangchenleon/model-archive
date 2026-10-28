"""Sticker codes.

Six characters of Crockford Base32: digits plus A-Z without I, L, O and U, so a
code typed from a phone keypad cannot be confused with another one. Codes are
random rather than sequential — the number on a sticker should say nothing about
how many kits you own or when you bought them.
"""

from __future__ import annotations

import re
import secrets

ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
LENGTH = 6

# Characters people confuse when reading a sticker, mapped to what they meant.
CONFUSABLE = str.maketrans({"O": "0", "I": "1", "L": "1", "U": "V"})

_CODE_RE = re.compile(r"^[0-9A-Z]{6}(-[2-9][0-9]?)?$")


def new_code() -> str:
    """A fresh asset code. Collisions are handled by the unique constraint and retry."""
    return "".join(secrets.choice(ALPHABET) for _ in range(LENGTH))


def normalise(raw: str) -> str:
    """Upper-case, drop separators, fold confusables: what the user typed → what we store."""
    value = re.sub(r"[^0-9A-Za-z-]", "", (raw or "")).upper().translate(CONFUSABLE)
    return value


def looks_like_code(raw: str) -> bool:
    return bool(_CODE_RE.match(normalise(raw)))
