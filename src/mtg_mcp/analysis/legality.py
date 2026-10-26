"""Copy limits and basic-land checks."""

from __future__ import annotations

import re
from typing import Any

from ..scryfall import oracle_text

_ANY_NUMBER = re.compile(r"a deck can have any number of cards named")
_UP_TO_N = re.compile(r"a deck can have up to (\w+) cards named")


def _is_basic(card: dict[str, Any]) -> bool:
    return "Basic" in (card.get("type_line") or "") and "Land" in (card.get("type_line") or "")


def _copy_limit(card: dict[str, Any], singleton: bool) -> int | None:
    """Max copies allowed; None means unlimited."""
    text = oracle_text(card).lower()
    if _is_basic(card) or _ANY_NUMBER.search(text):
        return None
    m = _UP_TO_N.search(text)
    if m:
        words = {"seven": 7, "nine": 9}
        return words.get(m.group(1), int(m.group(1)) if m.group(1).isdigit() else None)
    return 1 if singleton else 4
