---
name: moxfield-primer
description: >
  After a NeRo-style list is final: tag every card for Moxfield paste and write
  a copy-paste primer (plan, mulligan, win lines, key cards). Use when the user
  asks for Moxfield export, a primer, deck tags, or publishing the list.
---

# Moxfield primer and tagged list

Run this **after** the list passes `nero-build` or `nero-tune` (price, combos, goldfish already done). Do not tag a draft list you are still cutting.

If `analyze_deck` or `price_decklist` is not in this session, say so and stop.

## Inputs you must already have

From earlier skills, keep these in the reply (do not re-derive from memory):

- **Bend**, **When**, **Bar**, **Jobs** (`nero-read`, `defcat-read`)
- **Win lines** (`nero-lines`, `find_combos`, or `reference_deck` notes)
- **Goldfish block** (`nero-goldfish`) or `not simulated`
- **Price** and **land count** (`price_decklist`, `analyze_deck`)

## Order

```
analyze_deck(decklist)          roles + categories for tags
find_combos(decklist)             which cards are combo pieces
reference_deck(commander)       his primer shape, if it exists
tag every line                    see rules below
write primer markdown             sections below
```

1. `analyze_deck` on the final list. Use `roles.cards` and `categories` only as a **first pass**; fix obvious misses (a known `#combo` piece tagged only `#synergy`).
2. `find_combos` on the same list. Any card that appears in an **in_deck** line gets `#combo` unless it already carries a clearer plan tag (`#wincon`).
3. `reference_deck` when NeRo built this commander. Mirror his primer **sections**, not his card choices. Do not copy his paragraphs.

## Tag rules (Moxfield paste)

One card per line. Tags are **hashes at the end of the line**, lowercase, no spaces (use hyphens).

```text
1 Sol Ring #ramp
1 Counterspell #counter #removal
1 Forest #land
```

- **Every card** gets at least one tag. Lands and basics: `#land`.
- **At most three tags** per card. Prefer the job that mattered in the **bend**, not every Scryfall role.
- **Commanders** get the plan tag plus one role (`#synergy`, `#combo`, `#draw`, etc.).

Map `analyze_deck` roles to tags:

| Role | Tag |
|------|-----|
| ramp | `#ramp` |
| card_draw | `#draw` |
| removal | `#removal` |
| counterspell | `#counter` |
| board_wipe | `#wipe` |
| tutor | `#tutor` |
| (combo piece from find_combos) | `#combo` |
| (finisher / one-spell win) | `#wincon` |
| (other plan card) | `#synergy` or one **theme** tag (`#landfall`, `#-1-1`, `#elf`, …) |

Double-duty cards get two tags, e.g. `#ramp #draw`. Do not tag `#plan`.

Sort the main deck **mana value ascending**, then name. Keep commanders in a **Commander** block (see format).

## Decklist format to hand back

Two blocks the user can paste into Moxfield's bulk editor:

```text
// Commander
1 Commander Name #tag #tag

// Deck
1 Card A #ramp
1 Card B #draw #combo
...
```

Use `1` counts only (Moxfield accepts `1x` but stay consistent). No set codes unless the user asked for a shopping list with printings.

## Primer format (markdown for Moxfield)

Write **markdown only** — no chat wrapper, no "here is your primer". Headings use `##`. Keep it scannable; short paragraphs beat walls of text.

Required sections, in order:

1. **Suggested deck title** — one line, not in the primer body: `$100 {Commander} - High Power - {hook}` (hook = the bend in three words).
2. **Overview** — 2–4 sentences: bracket (~$100 high-power Bracket 4), what the deck is **not** (surface EDHREC theme), and the bend.
3. **Game plan** — ideal sequence using **When** from defcat-read; name the turn the commander wants to land.
4. **Mulligan** — concrete keeps (land count + one job card), one sentence on what to ship.
5. **Win conditions** — bullet list of lines from `find_combos` / notes; use card names exactly as in the list.
6. **How the lines work** — one short paragraph or bullet per line; a reader who owns the deck should know when to go off.
7. **Key cards** — 5–8 names that are not obvious; say **why** in a phrase each.
8. **Stats** — price (from `price_decklist`), land count, avg MV from `analyze_deck`, goldfish lines from `nero-goldfish` (or `not simulated`).

Optional when true: **Notable cuts** (1–3 cards you almost ran), **Upgrades** (if over budget).

Do not paste EDHREC's top cards as the plan. Do not invent combo steps — `get_card_rulings` first if timing matters.

## Hand back

Deliver **two fenced blocks** in this order:

1. ` ```text ` — tagged decklist (`// Commander` + `// Deck`).
2. ` ```markdown ` — full primer.

Then one line: **Title:** `{suggested title}`.

## Example (shape only)

```text
// Commander
1 Rowan, Scion of War #synergy #draw

// Deck
1 Vial Smasher the Fierce #synergy #combo
1 Sol Ring #ramp
...
```

```markdown
## Overview
...
## Game plan
...
```
