"""Asset lifecycle: the one place that decides which state may follow which.

``sold`` is a sink: any non-sold state may move there, nothing moves out. That
is not only a UI preference — the API, the bulk action and the drawer all read
this table so an "impossible" transition cannot be reached by one route while
being hidden by another.
"""

from __future__ import annotations

ASSET_STATES = ("pending", "keep", "displayed", "stored", "sold")

STATE_LABELS = {
    "pending": "待拼",
    "keep": "收藏",
    "displayed": "展示",
    "stored": "收纳",
    "sold": "卖出",
}

# Order matters: the drawer renders the tuple as-is, so the primary action
# comes first.
ALLOWED_TRANSITIONS: dict[str, tuple[str, ...]] = {
    "pending": ("displayed", "keep", "sold"),
    "keep": ("pending", "sold"),
    "displayed": ("stored", "sold"),
    "stored": ("displayed", "sold"),
    "sold": (),
}


def allowed_next_states(state: str) -> list[str]:
    return list(ALLOWED_TRANSITIONS.get(state, ()))
