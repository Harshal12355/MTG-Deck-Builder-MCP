"""Card-Forge rules & AI synergy tag parser (https://github.com/Card-Forge/forge).

Fetches a card's human-written `.txt` rules script from Card-Forge (`cardsfolder/`)
and extracts `DeckHas`, `DeckNeeds`, `DeckHints`, AI deck flags, and structured
ability/trigger AST nodes to cross-check regex role/synergy heuristics.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any

from .http import HttpClient

FORGE_RAW_BASE = "https://raw.githubusercontent.com/Card-Forge/forge/master/forge-gui/res/cardsfolder"
TTL_DAY = 86400.0


def forge_slug(name: str) -> str:
    """Convert a card name into its Card-Forge `cardsfolder/<letter>/<slug>.txt` path."""
    # Strip accents (e.g. Andúril -> Anduril, Lim-Dûl -> Lim-Dul)
    norm = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii").lower()
    # Replace non-alphanumeric separators (spaces, hyphens, slashes) with single underscores
    cleaned = re.sub(r"['\",.!?:;()]", "", norm)
    slug = re.sub(r"[^a-z0-9]+", "_", cleaned).strip("_")
    folder = slug[0] if slug else "a"
    return f"{folder}/{slug}.txt"


def _split_tag_expr(expr: str) -> list[str]:
    """Split a Forge tag expression like `Ability$Token & Type$Soldier` into clean tokens."""
    return [tok.strip() for tok in re.split(r"[&|]", expr) if tok.strip()]


def parse_forge_script(script: str) -> dict[str, Any]:
    """Parse a Card-Forge `.txt` card script into structured DeckHas/DeckNeeds/AST metadata."""
    deck_has: list[str] = []
    deck_needs: list[str] = []
    deck_hints: list[str] = []
    ai_flags: list[str] = []
    abilities: list[str] = []
    triggers: list[str] = []
    sac_costs: list[str] = []

    for raw in script.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("DeckHas:"):
            deck_has.extend(_split_tag_expr(line.split(":", 1)[1]))
        elif line.startswith("DeckNeeds:"):
            deck_needs.extend(_split_tag_expr(line.split(":", 1)[1]))
        elif line.startswith("DeckHints:"):
            deck_hints.extend(_split_tag_expr(line.split(":", 1)[1]))
        elif line.startswith("AI:"):
            ai_flags.append(line.split(":", 1)[1].strip())
        elif line.startswith(("A:", "SVar:")):
            for m in re.finditer(r"\b(?:AB|SP|DB)\$\s*([A-Za-z0-9_]+)", line):
                ab = m.group(1)
                if ab not in abilities:
                    abilities.append(ab)
            for m in re.finditer(r"Sac<[^/>]+/([^>]+)>", line):
                target = m.group(1).split("/")[0]
                if target not in sac_costs:
                    sac_costs.append(target)
        elif line.startswith("T:"):
            for m in re.finditer(r"\bMode\$\s*([A-Za-z0-9_]+)", line):
                trig = m.group(1)
                if trig not in triggers:
                    triggers.append(trig)

    # Derive explicit Enabler / Payoff synergy tags from DeckHas, DeckNeeds, and AST nodes
    enables: set[str] = set()
    needs_payoff: set[str] = set()
    all_has = " ".join(deck_has)
    all_needs = " ".join(deck_needs + deck_hints)

    if "Token" in all_has or "Token" in abilities:
        enables.add("tokens")
    if "Token" in all_needs:
        needs_payoff.add("tokens")
    if "Counters" in all_has or "Proliferate" in all_has or any(a in abilities for a in ("PutCounter", "PutCounterAll", "Proliferate")):
        enables.add("counters")
    if "Counters" in all_needs or "Proliferate" in all_needs:
        needs_payoff.add("counters")
    if sac_costs or "Sacrifice" in all_has:
        enables.add("sacrifice")
    if "Sacrifice" in all_needs or "Graveyard" in all_needs:
        needs_payoff.add("sacrifice")
    if any(a in abilities for a in ("Mill", "Discard", "Surveil")) or "Graveyard" in all_has or "Discard" in all_has:
        enables.add("graveyard")
    if "Graveyard" in all_needs or "Reanimate" in all_has:
        needs_payoff.add("graveyard")
    if "LifeGain" in all_has or "GainLife" in abilities:
        enables.add("lifegain")
    if "LifeGain" in all_needs:
        needs_payoff.add("lifegain")

    return {
        "deck_has": deck_has or None,
        "deck_needs": deck_needs or None,
        "deck_hints": deck_hints or None,
        "abilities": abilities or None,
        "triggers": triggers or None,
        "sacrifice_costs": sac_costs or None,
        "synergy_enables": sorted(enables) or None,
        "synergy_needs": sorted(needs_payoff) or None,
        "ai_flags": ai_flags or None,
    }


async def fetch_forge_tags(http: HttpClient, name: str) -> dict[str, Any] | None:
    """Fetch and parse a card's Card-Forge `.txt` script (tries full name, then front face)."""
    candidates = [forge_slug(name)]
    if "//" in name:
        front = forge_slug(name.split("//")[0].strip())
        if front not in candidates:
            candidates.append(front)
    for rel in candidates:
        text = await http.get_text(f"{FORGE_RAW_BASE}/{rel}", ttl=TTL_DAY, allow_404=True)
        if text:
            parsed = parse_forge_script(text)
            parsed["script_path"] = rel
            return parsed
    return None
