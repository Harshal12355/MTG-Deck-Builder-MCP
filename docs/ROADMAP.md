# Roadmap: DDIA, Efficiency & EDHcheck Tool Suite

Master plan for `mtg-deckbuilder-mcp`:
1. **Part 1 (Phases 1–5):** Data provenance, Moxfield ingestion, deterministic tagging, SQLite cache, and CI evals.
2. **Part 2 (Phase 6):** Making every existing tool faster (per-card caching, parallel host calls, `math.comb` exact math).
3. **Part 3 (Phases 7–10):** Building out the [EDHcheck tools](https://edhcheck.com/tools/) suite inside the MCP with zero extra dependencies.

```text
                       Decklist / URL / Pod Input
                                   │
                                   ▼
┌──────────────────────────────────────────────────────────────────────┐
│ 1. INGEST & CACHE (Phases 1, 2, 4, 6)                                │
│    moxfield_get_deck • archidekt_get_deck • Per-Card SQLite Cache    │
│    (Fetch only uncached cards; 80-card overlap = 20 cards fetched)   │
└──────────────────────────────────┬───────────────────────────────────┘
                                   │
         ┌─────────────────────────┼─────────────────────────┐
         ▼                         ▼                         ▼
┌─────────────────────┐   ┌─────────────────────┐   ┌─────────────────────┐
│ 2. SINGLE DECK      │   │ 3. MANA & TOKENS    │   │ 4. DIFF & POD       │
│ • analyze_deck      │   │ • analyze_mana_base │   │ • compare_decks     │
│   (+ WotC Bracket)  │   │ • search_lands      │   │   (A vs B delta)    │
│ • simulate_deck     │   │ • find_tokens       │   │ • check_pod         │
│   (+ Mulligan Calc) │   │   (via all_parts)   │   │   (up to 4 decks)   │
│ • price_decklist    │   └─────────────────────┘   └─────────────────────┘
│   (USD + EUR + swaps│
│ • tag_decklist      │
└─────────────────────┘
```

---

## Status & Time Estimates

### Part 1: Foundation & Moxfield Loop (Optional / Remaining)
- [ ] **Phase 1 (~20 min):** Snapshot provenance (`captured_at` on reference library tools)
- [ ] **Phase 2 (~35 min):** One-call Moxfield deck fetch (`moxfield_get_deck`)
- [ ] **Phase 3 (~40 min):** Deterministic Moxfield tagger (`tag_decklist`)
- [ ] **Phase 4 (~30 min):** Persistent SQLite HTTP cache across MCP restarts
- [x] **Phase 5 (~30 min):** Golden-deck & skill-chain regression evals in CI (`tests/test_regression.py`, `tests/fixtures/golden_atraxa_pipeline.json`)

### Part 2: Making Current Tools Faster (Shipped)
- [x] **Phase 6a (~30 min):** Per-card cache in `Scryfall.collection()` (stop re-fetching 75-card batches when 1 card changes)
- [x] **Phase 6b (~25 min):** Parallel upstream fetches (`asyncio.gather` across Scryfall + Spellbook, parallel alias lookups)
- [x] **Phase 6c (~35 min):** Upgrade `analyze_deck` (auto WotC Bracket 1–5, 0–10 Power, 3-School, 10-axis Synergy) & `price_decklist` (`eur` + `budget_target` cut suggestions)

### Part 3: EDHcheck Tool Suite (Shipped)
- [x] **Phase 7 (~45 min):** Mana Base Analysis & Land Database (`analyze_mana_base`, `search_lands`)
- [x] **Phase 8 (~45 min):** Mulligan Strategy Calculator, Single-Card Knockout Attribution & Color-Aware Goldfish (`simulate_deck` with `mulligan_targets` and `track_card_impact`)
- [x] **Phase 9 (~45 min):** Deck Compare & 4-Deck Pod Checker (`compare_decks`, `check_pod`)
- [x] **Phase 10 (~35 min):** Token Finder & Precon/Game-Changer helpers (`find_tokens`, `random_card` query filters)

---

## EDHcheck Coverage Map

| EDHcheck Tool | MCP Status | Shipped / Remaining Plan |
| :--- | :--- | :--- |
| **Deck Analysis** | **Shipped** (`analyze_deck`) | WotC Bracket 1–5 + `bracket_path`, 0–10 Power Score, 3-School Score, 10-axis `Enabler × Payoff` synergy, `include_combos=True` |
| **Deck Builder** | **Shipped** (`nero-build`, `deckbuilding_template`, `moxfield-primer`) | Optional Phase 3: `tag_decklist` deterministic helper |
| **Mana Base Analysis** | **Shipped** (`analyze_mana_base`) | Karsten 90% hypergeometric cast rates via `math.comb`, 0–100 grade (`S` to `D-`), tipping point, and cycle speed breakdown |
| **Land Database** | **Shipped** (`search_lands`) | 24 Commander land cycles (`fetch`, `shock`, `bond`, `pain`, `pathway`, `verge`, `surveil`...) filtered by identity, speed, and USD |
| **Deck Compare** | **Shipped** (`compare_decks`) | Single-batch Scryfall resolution with `cards_added`/`cards_removed`, `similarity_pct`, and bracket/power/speed/role/price deltas |
| **Pod Checker** | **Shipped** (`check_pod`) | 2–4 deck Rule 0 table balance (`balanced`, `slight`, `uneven`, `mismatched`), spread metrics, and per-seat disclosures |
| **Combo Finder** | **Shipped** (`find_combos`, `search_combos`) | Runs standalone or concurrently inside `analyze_deck(include_combos=True)` |
| **Game Changers List** | **Shipped** (`analyze_deck`, `search_cards`) | Full WotC Game Changers detection and bracket floor enforcement; queryable via `search_cards("is:gamechanger")` |
| **Token Finder** | **Shipped** (`find_tokens`) | Extracts token parts from Scryfall `all_parts` (`component == "token"`), doublers, and recommended copy counts |
| **Price Checker** | **Shipped** (`price_decklist`) | Supports `currency="usd"` (TCGplayer) and `currency="eur"` (Cardmarket) plus `budget_target` cut suggestions |
| **Deck Tester** | **Shipped** (`simulate_deck`) | Color-aware Monte Carlo goldfish with `track_card_impact=True` (single-card knockout attribution) |
| **Mulligan Calculator** | **Shipped** (`simulate_deck`) | Custom `mulligan_targets` (e.g. `[{"role": "land", "min": 2, "max": 4, "by_turn": 1}]`) + hypergeometric satisfaction rates |
| **Random Commander** | **Shipped** (`random_card`) | Scryfall query support (e.g. `is:commander id<=ubr usd<5`) |
| **Explore / Precons** | **Shipped** (`archidekt_*`, `reference_*`, `moxfield_import_user`) | Optional Phase 1–2: `captured_at` provenance field and one-call `moxfield_get_deck` |

---

## Part 1: Foundation & Moxfield Loop (Phases 1–5)

### Phase 1 — Snapshot Provenance (`phase-1-provenance`)
- **Estimate:** ~20 minutes
- **Why:** Live Scryfall calls are the source of truth; the bundled NeRo library is a capture-time snapshot. Stamping `captured_at` prevents stale prices from looking live.
- **Scope:**
  1. `src/mtg_mcp/moxfield.py`: write `"captured_at": YYYY-MM-DD` into `source.json` during `import_user`.
  2. `src/mtg_mcp/data/library/nero/source.json`: set `"captured_at": "2026-10-20"`.
  3. `src/mtg_mcp/library.py` & `src/mtg_mcp/tools/reference.py`: include `captured_at` in `reference_library`, `reference_deck`, `reference_cards`, and `reference_compare`.
  4. `tests/test_all.py`: assert `captured_at` on library outputs.

### Phase 2 — Symmetrical Moxfield Ingestion (`phase-2-moxfield-deck`)
- **Estimate:** ~35 minutes
- **Why:** Archidekt URLs work in one tool call (`archidekt_get_deck`), while Moxfield URLs require manual copy-paste even though `moxfield.py` already speaks Moxfield's JSON endpoints.
- **Scope:**
  1. `src/mtg_mcp/moxfield.py`: add `parse_moxfield_id(id_or_url)` and a summary helper returning `{commanders, decklist, card_count, tags, primer, url}`.
  2. `src/mtg_mcp/tools/reference.py`: register `@mcp.tool() async def moxfield_get_deck(deck_id_or_url: str, include_primer: bool = True)`.
  3. Update skills/rules and add round-trip tests in `tests/test_all.py`.

### Phase 3 — Deterministic Moxfield Tagger (`phase-3-tag-tool`)
- **Estimate:** ~40 minutes
- **Why:** Computing `#ramp`, `#draw`, `#combo`, and `#land` in Python from `card_roles` and library tags takes milliseconds and never drifts.
- **Scope:**
  1. `src/mtg_mcp/analysis/`: add `tag_deck(deck, cards, combo_cards, library_roles)`.
  2. `src/mtg_mcp/tools/deck.py`: expose `@mcp.tool() async def tag_decklist(decklist: str, commanders: list[str] | None = None)`.
  3. Update `moxfield-primer/SKILL.md` and `tests/test_all.py`.

### Phase 4 — Persistent SQLite TTL Cache (`phase-4-disk-cache`)
- **Estimate:** ~30 minutes
- **Why:** `TTLCache` in `src/mtg_mcp/http.py` is currently in-memory only; restarting the MCP server wipes all cached Scryfall and Spellbook responses.
- **Scope:**
  1. `src/mtg_mcp/http.py`: back `TTLCache` with stdlib `sqlite3` (`~/.cache/mtg-mcp/http_cache.sqlite3`, overridable via `MTG_MCP_CACHE_PATH`, in-memory for tests).
  2. `tests/test_all.py`: verify persistence across instances and TTL expiry.

### Phase 5 — Golden-Deck & Skill-Chain Evals (`phase-5-golden-evals`)
- **Estimate:** ~30 minutes
- **Scope:**
  1. `tests/test_all.py`: regex-scan all `get_skill("...")` calls across skills/rules and assert they exist in `load_skills()`.
  2. Add an end-to-end golden-deck test (`parse_decklist` → `analyze_deck` → `find_combos` → `simulate_deck(seed=1)` → `tag_decklist`).

---

## Part 2: Making Current Tools Faster (Phase 6)

```text
BEFORE (Batch-Keyed Cache):
analyze_deck(100 cards) ──► POST /cards/collection [75] + [25]  (2 HTTP calls)
compare_decks(+2 swaps) ──► Cache Key Miss! Re-fetches all 100  (2 HTTP calls)

AFTER (Per-Card Cache in Scryfall.collection):
analyze_deck(100 cards) ──► POST /cards/collection [75] + [25]  (cached by card name)
compare_decks(+2 swaps) ──► 98 hits in cache, fetches only [2]  (1 tiny HTTP call; 0 if cached)
```

### Phase 6a — Per-Card Resolution Cache (`phase-6a-card-cache`)
- **Estimate:** ~30 minutes
- **Bottleneck:** `HttpClient` caches `/cards/collection` by the exact JSON POST body of 75 cards. Changing 1 card in a deck invalidates the entire batch cache, and calling `analyze_deck` then `price_decklist` with slightly different board slices re-fetches all 100 cards.
- **Fix:**
  1. `src/mtg_mcp/scryfall.py`: in `Scryfall.collection()`, check `self.http.cache.get(f"card:{name_lower}")` for each unique card first.
  2. Only send *uncached* names to `/cards/collection`, then write each returned card into `card:{name_lower}` (and its front-face/flavor alias).
  3. Also populate `card:{name_lower}` when `Scryfall.named()` succeeds.

### Phase 6b — Parallel Host & Alias Execution (`phase-6b-concurrency`)
- **Estimate:** ~25 minutes
- **Bottleneck:**
  - `Scryfall.collection()` retries missed alias cards one-by-one in a `for` loop.
  - `Edhrec.commander()` resolves partner commanders sequentially.
  - `Archidekt.popular_cards()` fetches up to 30 decks strictly serially.
- **Fix:**
  1. Use `asyncio.gather` for alias lookups in `Scryfall.collection()` and partner resolution in `src/mtg_mcp/tools/edhrec_tools.py` (the per-host lock in `HttpClient._throttle` still enforces polite rate limits, while cached hits return in `0 ms`).
  2. Add optional `include_combos: bool = False` to `analyze_deck` (`src/mtg_mcp/tools/deck.py`) so Scryfall (`api.scryfall.com`) and Commander Spellbook (`backend.commanderspellbook.com`) run concurrently via `asyncio.gather`, cutting full-analysis wall time in half.

### Phase 6c — Richer `analyze_deck` (WotC Bracket) & `price_decklist` (EUR + Budget Swaps)
- **Estimate:** ~35 minutes
- **Scope:**
  1. `src/mtg_mcp/analysis/bracket.py` & `src/mtg_mcp/analysis/analyze.py`: heuristic WotC Bracket (1–5) estimation, 0–10 Power Score, 3-School Score, and 10-axis synergy in `analyze()` using Game Changers count (`0` → B1/2, `1–3` → B3, `4+` → B4), mass land denial regex, extra-turn regex, and tutor density.
  2. `src/mtg_mcp/scryfall.py` & `src/mtg_mcp/tools/deck.py`: `currency: Literal["usd", "eur"] = "usd"` and `budget_target` cut suggestions in `price_decklist` (Scryfall already returns `prices.eur` in the same payload, so zero extra API calls).

---

## Part 3: EDHcheck Tool Suite (Phases 7–10)

### Phase 7 — Mana Base Analysis & Land Database (`phase-7-mana-and-lands`)
- **Estimate:** ~45 minutes
- **Tools (`src/mtg_mcp/analysis/mana.py`, `src/mtg_mcp/tools/deck.py`):**
  1. `analyze_mana_base(decklist, commanders=None, budget_per_land=5.0)`:
     - Classifies every land by **speed** (`untapped`, `conditional`, `tapped`) and **cycle** (fetch, shock, bond/crowd, pain, check, slow, pathway, filter, surveil, verge, bounce, command, basic).
     - Uses `math.comb` (exact hypergeometric probability, `<1 ms`) to compute **on-curve cast rate** for the commander and for the deck's pip-heaviest spells (e.g. `Counterspell` on Turn 2, `Necropotence` on Turn 3).
     - Recommends specific budget land swaps when a color's cast rate is `<85%`.
  2. `search_lands(color_identity, cycle=None, speed=None, max_price=None)`:
     - Curated 24-cycle land table (`LAND_CYCLES`) in `src/mtg_mcp/analysis/mana.py` and `search_lands` in `src/mtg_mcp/tools/deck.py` so the model can pull exact cycles (e.g. Dimir untapped duals under $5) in one call.

### Phase 8 — Mulligan Calculator & Color-Aware Goldfish (`phase-8-mulligan-sim`)
- **Estimate:** ~45 minutes
- **Why:** The keep rule is still one hardcoded land count. Color, a payable win line, cards left in hand, and a non-ramp follow-up are already in `simulate_deck`.
- **Scope (`src/mtg_mcp/goldfish.py`):**
  1. Done: produced colors, commander pips, `assembled_by_turn` vs `seen_by_turn`, `development.median_hand_by_turn`, `development.follow_up_by_turn`.
  2. Still open: `mulligan_targets: list[dict] | None = None` (e.g. `[{"role": "land", "min": 2, "max": 4, "by_turn": 1}, {"role": "ramp", "min": 1, "by_turn": 2}]`) so it acts as EDHcheck's **Mulligan Strategy Calculator** across 10,000 trials.

### Phase 9 — Deck Compare & Pod Checker (`phase-9-compare-and-pod`)
- **Estimate:** ~45 minutes
- **Tools:**
  1. `compare_decks(decklist_a, decklist_b, commanders=None)`:
     - Resolves the union of both decks in **one** `scryfall.collection()` call.
     - Returns `cards_added`, `cards_removed`, and exact before/after diffs for average CMC, land count, role counts (ramp, draw, removal, wipes), Game Changers, and total price.
  2. `check_pod(decks: list[str], names: list[str] | None = None)`:
     - Accepts 2–4 decklists (or Archidekt/Moxfield URLs), resolves all unique cards in a single shared cache pass, runs `analyze` + fast `simulate(trials=1000)` on each, and outputs a **Rule 0 Pod Report**: bracket spread, fastest/slowest median commander turn, Game Changer counts, and mismatch warnings.

### Phase 10 — Token Finder & Commander Generator (`phase-10-tokens-and-extras`)
- **Estimate:** ~35 minutes
- **Tools:**
  1. `find_tokens(decklist)`:
     - Reads `all_parts` (`component == "token"`) from the already-fetched Scryfall card dicts (zero extra calls to discover tokens; one `/cards/collection` call by Scryfall ID to get token P/T, colors, oracle text, and double-faced token pairings) and lists which deck cards create each token.
  2. Enhance `random_card` with optional `is_commander: bool = False`, `color_identity: str | None = None`, `max_cmc: float | None = None`, `max_usd: float | None = None` to cover EDHcheck's **Random Commander Generator** without adding a redundant tool.

---

## Code structure (see `docs/architecture.md`)

Modularization follows MCP reference-server patterns: thin `server.py` + `tools/*`, domain in `analysis/*`, shared `wiring.py`. Progress is tracked in the architecture doc migration checklist (golden tests gate each step).

---

## Explicitly Out of Scope (Ponytail YAGNI)

- **EDHcheck UI-only games & bots:** *Higher or Lower Price Game*, *MTG Oracle (20 Questions)*, *Pack Simulator (foil shimmer UI)*, and *Discord Bot* are web-entertainment / chat-platform wrappers, not deckbuilding MCP primitives.
- **Airflow / Celery / Redis / Vector DBs:** single-process `sqlite3` + in-memory JSON handles all caching and library queries in milliseconds with zero external services.
