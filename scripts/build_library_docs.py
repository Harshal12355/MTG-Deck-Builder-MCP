"""Render the reference library (src/mtg_mcp/data/library) as markdown under docs/library/.

    python scripts/build_library_docs.py

Writes, per source: PRINCIPLES.md, CARD_LIBRARY.md (every card by role, staples first) and DECKS.md
(each deck's plan, win lines and stats). Re-run after moxfield_import_user or after editing notes.
"""

from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from mtg_mcp.library import ROLES, Library, deck_label  # noqa: E402

ROLE_TITLES = {
    "ramp": "Ramp & fast mana", "draw": "Card advantage", "tutor": "Tutors", "counter": "Counterspells",
    "removal": "Removal", "wipe": "Board wipes", "protection": "Protection", "stax": "Stax & hate",
    "combo": "Combo pieces", "recursion": "Recursion", "untap": "Untappers", "clone": "Clones & copies",
    "tokens": "Token makers", "evasion": "Evasion", "land": "Lands", "other": "Untagged / theme cards",
}


def _price(v):
    return "–" if v is None else f"${v:.2f}"


def _mv(v):
    return "–" if v is None else (str(int(v)) if float(v).is_integer() else str(v))


def card_library_md(lib: Library, key: str) -> str:
    decks = [d for d in lib.active_decks() if d["source"] == key]
    n = len(decks)
    lines = [f"# Card library — {lib.sources[key].get('author', key)}", "",
             f"Every card played across {n} decks, grouped by the builder's own role tags and ranked by how many "
             "decks play it. **Decks** = number of his decks that run it. Prices are USD for the printing in his list "
             "at capture time. Re-check before buying. Basic lands are omitted.", "",
             "Query the same data live with the `reference_cards` / `reference_card` MCP tools.", ""]
    staples = lib.search_cards(min_decks=5, include_basics=False, limit=1000)
    lines += ["## Staples (in 5+ decks)", "", "| Card | Decks | MV | Colours | Price | Roles |", "|---|---|---|---|---|---|"]
    for c in staples:
        lines.append(f"| {c['name']} | {c['deck_count']} | {_mv(c['mana_value'])} | {c['color_identity'] or 'C'} | "
                     f"{_price(c['usd_at_capture'])} | {', '.join(c['roles'])} |")
    by_role: dict[str, list] = defaultdict(list)
    for c in lib.search_cards(min_decks=1, limit=100000):
        by_role[c["roles"][0] if c["roles"] else "other"].append(c)
    for role in ROLES + ["other"]:
        cards = by_role.get(role)
        if not cards:
            continue
        lines += ["", f"## {ROLE_TITLES.get(role, role)} ({len(cards)})", "",
                  "| Card | Decks | MV | Colours | Price | Used in |", "|---|---|---|---|---|---|"]
        for c in cards:
            used = ", ".join(c["decks"][:6]) + (f" +{len(c['decks']) - 6}" if len(c["decks"]) > 6 else "")
            lines.append(f"| {c['name']} | {c['deck_count']} | {_mv(c['mana_value'])} | {c['color_identity'] or 'C'} | "
                         f"{_price(c['usd_at_capture'])} | {used} |")
    considering = sorted(((name, u["considering"]) for name, u in lib.usage.items() if u["considering"] and not u["decks"]),
                         key=lambda x: (-len(x[1]), x[0]))
    if considering:
        lines += ["", f"## Considering only ({len(considering)})", "",
                  "Cards in his maybeboards that no deck plays yet. Often budget wishlist items or cuts.", ""]
        lines += [f"- {name} — {', '.join(sorted(set(where)))}" for name, where in considering]
    return "\n".join(lines) + "\n"


def principles_md(lib: Library, key: str) -> str:
    s = lib.sources[key]
    lines = [f"# Deckbuilding principles — {s.get('author', key)}", "", s.get("summary", ""), "",
             f"Profile: {s.get('profile_url', '')}  ·  Captured: {s.get('captured', '')}", "",
             "Distilled from his primers and lists (paraphrased). Also served by the `reference_principles` MCP tool.", ""]
    for i, p in enumerate(s.get("principles", []), 1):
        lines += [f"## {i}. {p['title']}", "", p["guidance"], "", f"*Seen in:* {', '.join(p.get('evidence', []))}", ""]
    if s.get("rules_of_thumb"):
        lines += ["## Rules of thumb", ""] + [f"- {r}" for r in s["rules_of_thumb"]]
    return "\n".join(lines) + "\n"


def decks_md(lib: Library, key: str) -> str:
    lines = [f"# Decks — {lib.sources[key].get('author', key)}", "",
             "Sorted by views. Full lists: `reference_deck` MCP tool (its `decklist` feeds analyze_deck, and its "
             "win lines feed simulate_deck).", "",
             "| Deck | Commander(s) | Colours | Bracket | Lands | Avg MV | Price now* | Views | Updated |",
             "|---|---|---|---|---|---|---|---|---|"]
    decks = [d for d in lib.decks if d["source"] == key]
    for d in decks:
        st = lib.deck_stats(d)
        tag = " (placeholder, ignored)" if d.get("placeholder") else ""
        lines.append(f"| [{deck_label(d)}]({d.get('url')}){tag} | {' + '.join(d.get('commanders', []))} | {d.get('colors')} | "
                     f"{d.get('bracket')} | {st['lands']} | {st['average_mana_value_nonland']} | "
                     f"${st['price_usd_at_capture_excl_basics']:.0f} | {d.get('views')} | {d.get('updated')} |")
    lines += ["", "*Sum of the listed printings at capture time, excluding basics. Cheapest printings are usually lower.", ""]
    for d in decks:
        notes = d.get("notes", {})
        if not notes.get("plan") and not notes.get("win_lines"):
            continue
        lines += [f"## {deck_label(d)} — {notes.get('archetype', '')}", "", f"[{d['name']}]({d.get('url')})", ""]
        for label, k in (("Plan", "plan"), ("Ideal turn", "ideal_turn"), ("Mulligan", "mulligan"), ("Cuts", "cut_notes")):
            if notes.get(k):
                lines += [f"**{label}:** {notes[k]}", ""]
        if notes.get("win_lines"):
            lines += ["**Win lines:**", ""] + [f"- {' + '.join(w)}" for w in notes["win_lines"]] + [""]
        if notes.get("win_lines_needing_cards"):
            lines += ["**Mentioned lines needing cards not in the list:**", ""]
            lines += [f"- {' + '.join(w['cards'])} (missing: {', '.join(w['not_in_list'])})" for w in notes["win_lines_needing_cards"]]
            lines.append("")
        if notes.get("line_notes"):
            lines += ["**How the lines work:**", ""] + [f"- {x}" for x in notes["line_notes"]] + [""]
        if notes.get("key_cards"):
            lines += [f"**Key cards:** {', '.join(notes['key_cards'])}", ""]
        if notes.get("budget_wishlist"):
            lines += [f"**Would add with more budget:** {', '.join(notes['budget_wishlist'])}", ""]
    return "\n".join(lines) + "\n"


def main() -> None:
    lib = Library()
    out_root = ROOT / "docs" / "library"
    index = ["# Reference library", "", "Real, tested decklists from builders we learn from. Data: "
             "`src/mtg_mcp/data/library/`. MCP tools: `reference_library`, `reference_principles`, `reference_cards`, "
             "`reference_card`, `reference_deck`, `reference_compare`, `moxfield_import_user`.", ""]
    for key, s in lib.sources.items():
        folder = out_root / key
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "PRINCIPLES.md").write_text(principles_md(lib, key))
        (folder / "CARD_LIBRARY.md").write_text(card_library_md(lib, key))
        (folder / "DECKS.md").write_text(decks_md(lib, key))
        index.append(f"- **{s.get('author', key)}**: [principles]({key}/PRINCIPLES.md) · "
                     f"[card library]({key}/CARD_LIBRARY.md) · [decks]({key}/DECKS.md)")
        print(f"wrote {folder}")
    (out_root / "README.md").write_text("\n".join(index) + "\n")


if __name__ == "__main__":
    main()
