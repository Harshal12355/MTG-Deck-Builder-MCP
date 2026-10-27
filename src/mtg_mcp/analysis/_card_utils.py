"""Card name and mana-pip helpers."""

from __future__ import annotations

import re
from collections import Counter

COLORS = "WUBRG"

_PIP = re.compile(r"\{([^}]+)\}")


def _pips(cost: str) -> Counter[str]:
    pips: Counter[str] = Counter()
    for sym in _PIP.findall(cost or ""):
        if "/" in sym and any(ch.isdigit() for ch in sym):
            continue
        for c in COLORS:
            if c in sym.upper():
                pips[c] += 1
    return pips


def _front_lower(name: str) -> str:
    return name.split(" // ")[0].strip().lower()
