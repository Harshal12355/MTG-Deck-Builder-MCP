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

### Part 1: Foundation & Moxfield Loop (~2.5 hours total)
- [ ] **Phase 1 (~20 min):** Snapshot provenance (`captured_at` on reference library tools)
- [ ] **Phase 2 (~35 min):** One-call Moxfield deck fetch (`moxfield_get_deck`)
- [ ] **Phase 3 (~40 min):** Deterministic Moxfield tagger (`tag_decklist`)
- [ ] **Phase 4 (~30 min):** Persistent SQLite HTTP cache across MCP restarts
- [ ] **Phase 5 (~30 min):** Golden-deck & skill-chain regression evals in CI

### Part 2: Making Current Tools Faster (~1.5 hours total)
- [ ] **Phase 6a (~30 min):** Per-card cache in `Scryfall.collection()` (stop re-fetching 75-card batches when 1 card changes)
- [ ] **Phase 6b (~25 min):** Parallel upstream fetches (`asyncio.gather` across Scryfall + Spellbook, parallel alias lookups)
- [ ] **Phase 6c (~35 min):** Upgrade `analyze_deck` (auto WotC Bracket 1–5 score) & `price_decklist` (EUR + cheapest-printing swaps)

### Part 3: EDHcheck Tool Suite (~3.5 hours total)
- [ ] **Phase 7 (~45 min):** Mana Base Analysis & Land Database (`analyze_mana_base`, `search_lands`)
- [ ] **Phase 8 (~45 min):** Mulligan Strategy Calculator & Color-Aware Goldfish (extend `simulate_deck`)
- [ ] **Phase 9 (~45 min):** Deck Compare & 4-Deck Pod Checker (`compare_decks`, `check_pod`)
- [ ] **Phase 10 (~35 min):** Token Finder & Precon/Game-Changer helpers (`find_tokens`, `random_card` commander filters)

---

## EDHcheck Coverage Map

| EDHcheck Tool | MCP Status | Plan |
| :--- | :--- | :--- |
| **Deck Analysis** | Have `analyze_deck` | **Phase 6c:** Add WotC Bracket 1–5 estimator (Game Changers, MLD, extra turns, 2-card combos) |
| **Deck Builder** | Have `nero-build` + template | **Phase 3:** Add `tag_decklist` for instant Moxfield export |
| **Mana Base Analysis** | Partial (pips vs sources) | **Phase 7:** Add `analyze_mana_base` (on-curve cast % via `math.comb`, tap/untap ratio, land upgrades) |
| **Land Database** | Missing | **Phase 7:** Add `search_lands` (filter by cycle: fetch, shock, bond, pain, pathway, verge, speed, USD) |
| **Deck Compare** | Missing | **Phase 9:** Add `compare_decks` (cards in/out, curve/role/bracket/price deltas in 1 Scryfall batch) |
| **Pod Checker** | Missing | **Phase 9:** Add `check_pod` (compare 2–4 decks on bracket, speed, combos, and Rule 0 flags) |
| **Combo Finder** | Have `find_combos` / `search_combos` | **Phase 6b:** Run concurrently with Scryfall resolution |
| **Game Changers List** | Partial (`game_changer` bool) | **Phase 6c:** Explain bracket impact in `analyze_deck`; queryable via `search_cards("is:gamechanger")` |
| **Token Finder** | Missing | **Phase 10:** Add `find_tokens` using Scryfall `all_parts` (`component == "token"`) |
| **Price Checker** | Have `price_decklist` (USD) | **Phase 6c:** Add `currency="eur"` (Cardmarket) + `cheaper_printings_over` budget swap finder |
| **Deck Tester** | Have `simulate_deck` | **Phase 8:** Add color-aware mana checking so color-screwed hands don't count as castable |
| **Mulligan Calculator** | Hardcoded keep rule | **Phase 8:** Add custom `mulligan_targets` (e.g. "2+ lands, 1+ ramp by T2") + exact hypergeometric math |
| **Random Commander** | Have `random_card` | **Phase 10:** Add commander filter presets (color identity, max CMC, max USD) |
| **Explore / Precons** | Have `archidekt_*` & `reference_*` | **Phase 2 & 10:** Add `moxfield_get_deck` + precon search filter (`is:precon` / Archidekt precon filter) |

---

## Part 1: Foundation & Moxfield Loop (Phases 1–5)

### Phase 1 — Snapshot Provenance (`phase-1-provenance`)
- **Estimate:** ~20 minutes
- **Why:** Live Scryfall calls are the source of truth; the bundled NeRo library is a capture-time snapshot. Stamping `captured_at` prevents stale prices from looking live.
- **Scope:**
  1. `src/mtg_mcp/moxfield.py`: write `"captured_at": YYYY-MM-DD` into `source.json` during `import_user`.
  2. `src/mtg_mcp/data/library/nero/source.json`: set `"captured_at": "2026-10-20"`.
  3. `src/mtg_mcp/library.py` & `src/mtg_mcp/server.py`: include `captured_at` in `reference_library`, `reference_deck`, `reference_cards`, and `reference_compare`.
  4. `tests/test_all.py`: assert `captured_at` on library outputs.

### Phase 2 — Symmetrical Moxfield Ingestion (`phase-2-moxfield-deck`)
- **Estimate:** ~35 minutes
- **Why:** Archidekt URLs work in one tool call (`archidekt_get_deck`), while Moxfield URLs require manual copy-paste even though `moxfield.py` already speaks Moxfield's JSON endpoints.
- **Scope:**
  1. `src/mtg_mcp/moxfield.py`: add `parse_moxfield_id(id_or_url)` and a summary helper returning `{commanders, decklist, card_count, tags, primer, url}`.
  2. `src/mtg_mcp/server.py`: register `@mcp.tool() async def moxfield_get_deck(deck_id_or_url: str, include_primer: bool = True)`.
  3. Update skills/rules and add round-trip tests in `tests/test_all.py`.

### Phase 3 — Deterministic Moxfield Tagger (`phase-3-tag-tool`)
- **Estimate:** ~40 minutes
- **Why:** Computing `#ramp`, `#draw`, `#combo`, and `#land` in Python from `card_roles` and library tags takes milliseconds and never drifts.
- **Scope:**
  1. `src/mtg_mcp/analysis.py`: add `tag_deck(deck, cards, combo_cards, library_roles)`.
  2. `src/mtg_mcp/server.py`: expose `@mcp.tool() async def tag_decklist(decklist: str, commanders: list[str] | None = None)`.
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
  1. Use `asyncio.gather` for alias lookups in `Scryfall.collection()` and partner resolution in `server.py` (the per-host lock in `HttpClient._throttle` still enforces polite rate limits, while cached hits return in `0 ms`).
  2. Add optional `include_combos: bool = False` to `analyze_deck` so Scryfall (`api.scryfall.com`) and Commander Spellbook (`backend.commanderspellbook.com`) run concurrently via `asyncio.gather`, cutting full-analysis wall time in half.

### Phase 6c — Richer `analyze_deck` (WotC Bracket) & `price_decklist` (EUR + Budget Swaps)
- **Estimate:** ~35 minutes
- **Scope:**
  1. `src/mtg_mcp/analysis.py`: add heuristic WotC Bracket (1–5) estimation to `analyze()` using Game Changers count (`0` → B1/2, `1–3` → B3, `4+` → B4), mass land denial regex, extra-turn regex, and tutor density.
  2. `src/mtg_mcp/scryfall.py` & `src/mtg_mcp/server.py`: add `currency: Literal["usd", "eur"] = "usd"` to `price_decklist` (Scryfall already returns `prices.eur` in the same payload, so zero extra API calls) plus `cheaper_over: float | None = None` to automatically fetch the cheapest printing for any card above that threshold.

---

## Part 3: EDHcheck Tool Suite (Phases 7–10)

### Phase 7 — Mana Base Analysis & Land Database (`phase-7-mana-and-lands`)
- **Estimate:** ~45 minutes
- **Tools:**
  1. `analyze_mana_base(decklist, commanders=None, budget_per_land=5.0)`:
     - Classifies every land by **speed** (`untapped`, `conditional`, `tapped`) and **cycle** (fetch, shock, bond/crowd, pain, check, slow, pathway, filter, surveil, verge, bounce, command, basic).
     - Uses `math.comb` (exact hypergeometric probability, `<1 ms`) to compute **on-curve cast rate** for the commander and for the deck's pip-heaviest spells (e.g. `Counterspell` on Turn 2, `Necropotence` on Turn 3).
     - Recommends specific budget land swaps when a color's cast rate is `<85%`.
  2. `search_lands(color_identity, cycle=None, speed=None, max_price=None)`:
     - Curated cycle-to-Scryfall-query table in a new `src/mtg_mcp/lands.py` (~120 lines) so the model can pull exact cycles (e.g. Dimir untapped duals under $5) in one call.

### Phase 8 — Mulligan Calculator & Color-Aware Goldfish (`phase-8-mulligan-sim`)
- **Estimate:** ~45 minutes
- **Why:** `simulate_deck` currently ignores mana colors (`"Mana is counted by amount, not colour"`) and uses one hardcoded mulligan rule.
- **Scope (`src/mtg_mcp/goldfish.py`):**
  1. Track produced colors on `SimCard` (`produced_mana` from Scryfall) and check color requirements when casting the commander.
  2. Add `mulligan_targets: list[dict] | None = None` to `simulate_deck` (e.g. `[{"role": "land", "min": 2, "max": 4, "by_turn": 1}, {"role": "ramp", "min": 1, "by_turn": 2}]`) so it acts as EDHcheck's **Mulligan Strategy Calculator** across 10,000 trials.

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

## Explicitly Out of Scope (Ponytail YAGNI)

- **EDHcheck UI-only games & bots:** *Higher or Lower Price Game*, *MTG Oracle (20 Questions)*, *Pack Simulator (foil shimmer UI)*, and *Discord Bot* are web-entertainment / chat-platform wrappers, not deckbuilding MCP primitives.
- **Airflow / Celery / Redis / Vector DBs:** single-process `sqlite3` + in-memory JSON handles all caching and library queries in milliseconds with zero external services.
