"""Sticker codes.

Five characters of Crockford Base32: digits plus A-Z without I, L, O and U, so a
code typed on a phone keypad cannot be confused with another one. Codes are
random rather than sequential — the number on a sticker should say nothing about
how many kits you own — and every sticker gets its own, including a second bag
of the same kit.
"""

from __future__ import annotations

import re
import secrets

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Asset, AssetTag
from app.services.errors import Conflict

ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
LENGTH = 5
ATTEMPTS = 20

# Characters people confuse when reading a sticker, mapped to what they meant.
CONFUSABLE = str.maketrans({"O": "0", "I": "1", "L": "1", "U": "V"})

_CODE_RE = re.compile(r"^[0-9A-Z]{5}$")


def new_code() -> str:
    return "".join(secrets.choice(ALPHABET) for _ in range(LENGTH))


def normalise(raw: str) -> str:
    """Upper-case, drop separators, fold confusables: what the user typed → what we store."""
    return re.sub(r"[^0-9A-Za-z]", "", (raw or "")).upper().translate(CONFUSABLE)


def looks_like_code(raw: str) -> bool:
    return bool(_CODE_RE.match(normalise(raw)))


def issue(session: Session, count: int = 1) -> list[str]:
    """Allocate unused codes.

    Assets and stickers share one namespace, so looking a code up is never
    ambiguous; the caller's tables are checked before every hand-out.
    """
    issued: list[str] = []
    for _ in range(count):
        for _attempt in range(ATTEMPTS):
            code = new_code()
            if code in issued:
                continue
            if session.scalar(select(Asset.id).where(Asset.code == code)) is not None:
                continue
            if session.scalar(select(AssetTag.id).where(AssetTag.code == code)) is not None:
                continue
            issued.append(code)
            break
        else:
            raise Conflict("编号生成失败，请重试")
    return issued
