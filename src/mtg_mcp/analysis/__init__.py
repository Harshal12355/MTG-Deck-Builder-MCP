"""Deck analysis: legality, roles, bracket, mana base, compare, pod, tokens."""

from .analyze import analyze
from .compare import compare_decks_analysis
from .mana import LAND_CYCLES, analyze_mana
from .pod import evaluate_pod
from .roles import card_roles
from .template import TEMPLATE_CATEGORIES, resolve_template, template_overlap
from .tokens import collect_deck_tokens

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
