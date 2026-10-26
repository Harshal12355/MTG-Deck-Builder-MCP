#!/usr/bin/env python3
"""One-shot split of analysis/core.py into submodules. Run from repo root."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "src" / "mtg_mcp" / "analysis"
CORE = ROOT / "core.py"


def lines() -> list[str]:
    return CORE.read_text(encoding="utf-8").splitlines(keepends=True)


def chunk(start: int, end: int) -> str:
    """Inclusive 1-based line numbers."""
    return "".join(lines()[start - 1 : end])


def write(name: str, header: str, body: str) -> None:
    path = ROOT / name
    path.write_text(header + body, encoding="utf-8")
    print("wrote", path, "lines", body.count("\n"))


def main() -> None:
    if not CORE.is_file():
        raise SystemExit("core.py missing")

    write(
        "_card_utils.py",
        '''"""Card name and mana-pip helpers."""

from __future__ import annotations

import re
from collections import Counter

''',
        chunk(18, 18)
        + "\n\n"
        + chunk(378, 380)
        + "\n\n"
        + chunk(431, 443),
    )

    write(
        "roles.py",
        '''"""Heuristic deck roles from oracle text."""

from __future__ import annotations

import re
from typing import Any

from ..scryfall import front_type_line, oracle_text

''',
        chunk(332, 428),
    )

    write(
        "template.py",
        '''"""Command Zone deckbuilding template targets and reports."""

from __future__ import annotations

from typing import Any

from .roles import card_roles

''',
        chunk(218, 330),
    )

    write(
        "bracket.py",
        '''"""WotC bracket, power score, school score, and synergy."""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from typing import Any

from ..scryfall import front_type_line, oracle_text
from ._card_utils import COLORS, _front_lower
from .roles import card_roles

''',
        chunk(20, 189) + chunk(446, 901),
    )

    write(
        "mana.py",
        '''"""Mana base grade, Karsten math, and land cycle metadata."""

from __future__ import annotations

import math
import re
from collections import Counter
from typing import Any

from ..decklist import ParsedDeck
from ..scryfall import front_type_line, oracle_text
from ._card_utils import COLORS, _front_lower, _pips
from .roles import card_roles

''',
        chunk(191, 216) + "\n\n" + chunk(906, 1176),
    )

    write(
        "compare.py",
        '''"""Side-by-side deck comparison."""

from __future__ import annotations

from collections import Counter
from typing import Any

from ..decklist import ParsedDeck

''',
        chunk(1179, 1238).replace(
            "    rep_a = analyze(deck_a, cards)",
            "    from .analyze import analyze\n\n    rep_a = analyze(deck_a, cards)",
        ),
    )

    write(
        "pod.py",
        '''"""Multi-deck Rule 0 pod balance."""

from __future__ import annotations

from typing import Any

''',
        chunk(1241, 1325),
    )

    write(
        "tokens.py",
        '''"""Token checklist for a deck."""

from __future__ import annotations

import re
from typing import Any

from ..decklist import ParsedDeck
from ..scryfall import oracle_text
from ._card_utils import _front_lower

''',
        chunk(1328, 1425),
    )

    write(
        "legality.py",
        '''"""Copy limits and basic-land checks."""

from __future__ import annotations

import re
from typing import Any

from ..scryfall import oracle_text

_ANY_NUMBER = re.compile(r"a deck can have any number of cards named")
_UP_TO_N = re.compile(r"a deck can have up to (\\w+) cards named")


''',
        chunk(1428, 1441),
    )

    write(
        "analyze.py",
        '''"""Full deck analysis orchestrator."""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

from ..decklist import ParsedDeck
from ..scryfall import front_type_line, oracle_text, price_usd
from ._card_utils import COLORS, _pips
from .bracket import _is_game_changer, _score_and_bracket
from .legality import _copy_limit
from .roles import card_roles
from .template import _ENTRY_CATEGORY_TO_ROLE, _template_report, resolve_template

''',
        chunk(1444, 1619),
    )

    CORE.unlink()
    print("removed core.py")


if __name__ == "__main__":
    main()
