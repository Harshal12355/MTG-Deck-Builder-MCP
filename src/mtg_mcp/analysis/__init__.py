"""Deck analysis: legality, roles, bracket, mana base, compare, pod, tokens.

Implementation is split across submodules over time; import from ``mtg_mcp.analysis``
(not from ``analysis.core``) so callers stay stable.
"""

from .core import (
    LAND_CYCLES,
    TEMPLATE_CATEGORIES,
    analyze,
    analyze_mana,
    card_roles,
    collect_deck_tokens,
    compare_decks_analysis,
    evaluate_pod,
    resolve_template,
    template_overlap,
)

__all__ = [
    "LAND_CYCLES",
    "TEMPLATE_CATEGORIES",
    "analyze",
    "analyze_mana",
    "card_roles",
    "collect_deck_tokens",
    "compare_decks_analysis",
    "evaluate_pod",
    "resolve_template",
    "template_overlap",
]
