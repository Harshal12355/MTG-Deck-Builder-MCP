# Equipment Recommendation Algorithm

Instructions and context for AI agents working on the barge/tug recommendation system.

---

## 1. Overview

The equipment recommendation algorithm helps dispatchers answer: **given a shipment request (signal), what is the optimal combination of assets to deliver it at the lowest cost?**

Dispatchers/Commercial Operators receive shipment requests and must schedule equipment (barges + tugs) to cover them. The algorithm automates the initial recommendation, ranking candidates by distance, cargo compatibility, capacity fit, and cost.

### Long-term vision

Today the algorithm covers inland barges and tugs. Over time it will expand to:

- **Blue water vessels / ships** — extend the asset pool beyond inland barges to include ocean-going vessels, with their own capacity models, speed profiles, and rate structures.
- **Multi-signal batch optimization** — instead of optimizing one shipment at a time, optimize across a batch of signals simultaneously to find the globally optimal fleet assignment that covers all shipments at the lowest total cost.
- **Equipment-type recommendations** — support recommending the number and type of equipment needed (e.g. "2 x 10k bbl tank barges + 1 tug") rather than specific named assets. This answers both "how many barges do I need?" and "what class of equipment?" for cases where the user cannot select individual assets and only needs to know what to request from a carrier.

### Entry point

```python
simple_recommend_assets_for_shipment(
    shipment: ShipmentRequest,
    only_recent_tows_voyages: bool = True,
    only_active_voyages: bool = False,
    flexible_dates: bool = False,
    exclude_barge_ids: list[int] | None = None,
    prior_product_ids: list[int] | None = None,
    linehaul_stale_hours: int = LINEHAUL_STALE_HOURS,
    limit: int = 4,
) -> list[BargeRecommendation]
```

- **flexible_dates**: If `True`, availability score is not included in ranking (availability_score = 0). Use when load dates are flexible and laycan fit should not penalize recommendations.
- **linehaul_stale_hours**: Max hours between linehaul barge availability and load laycan for voyage options. Defaults to 72. API query param: `linehaul_stale_hours`.
- **exclude_barge_ids**: Barge IDs to exclude from the recommendation pool. API: repeat query param `exclude_barge=1&exclude_barge=2` for multiple.
- **recommendation_groups** (on the ShipmentRequest): When `shipment.recommendation_groups` is set, restricts the barge pool to only barges on tows shared with those groups (via `SharedObject`). If empty, the full company barge pool is used.
File: `webatds/helpers/predictions/simple_equipment_recommendation.py`

### Key domain terms

| Term | Meaning |
|------|---------|
| **ShipmentRequest** (signal) | A customer request to move cargo between two ports by a date range |
| **Voyage** | A scheduled trip with one or more sailing legs (SubServices) |
| **SubService** (sailing/leg) | A single origin-to-destination leg within a voyage |
| **SailingAsset** | Links an asset (barge or tug) to a SubService |
| **Tow** | A contract-based grouping of assets at a fleeting port |
| **Carrier** | The company operating the tug/barge; carriers generally do not move each other's barges |
| **Linehaul** | A service type where the carrier charges a freight rate i.e contract of affreightment (COA) (vs. dedicated day rates) |
| **Dedicated** | A service type where the shipper pays day rates for exclusive use of tug + barges |
| **TowingTariff / TowingTariffRate** | Rate cards for linehaul service (COA rates), filtered by product, date, unit, size |

---

## 2. Architecture and Data Flow

### Pipeline

```text
ShipmentRequest
 │
 ├─ BargeRecommendationEngine.__init__(..., flexible_dates=False, exclude_barge_ids=())
 │    Sets load_date, load_window_end; flexible_dates skips availability; exclude_barge_ids removed from pool
 │
 ├─ build_barge_candidates() -> list[BargeData]
 │    1. All company barges (non-deleted), excluding exclude_barge_ids
 │    2. Filter: recent tows/voyages (voyage latest_arrival within 30 days, or on active tow)
 │    3. Filter: active voyages only (tracking-enabled voyages + linehaul carrier validation)
 │    4. Filter: recommendation groups (only barges on tows shared with shipment.recommendation_groups; skipped if empty)
 │    5. Filter: product type compatibility (liquid barge classes vs dry barge classes)
 │    6. Filter: availability (exclude barges on committed voyages overlapping load_date ± 3 days)
 │    7. Bulk query: voyage data, tow data, locations, products, distances
 │    8. Company 420 only: if a voyage candidate has no product, use the most recent
 │        past categorized SailingAssetProduct on a current sailing (skip empty /
 │        outdated sailings; tow-only candidates are not looked up)
 │    9. Filter: prior_product_ids (optional API allowlist of prior cargo)
 │    10. Pre-fetch cleaning costs from MatrixEntry
 │    11. Company 420 only: hard-filter by parent family (matrix compatible overrides;
 │        not_compatible drops)
 │    12. Sort by distance to origin
 │
 ├─ create_combinations(barge_candidates) -> list[list[BargeData]]
 │    1. Group by carrier (carrier isolation rule)
 │    2. Within each carrier: group by voyage ID (prefer existing groupings)
 │    3. Within each carrier: group by tow ID (remaining barges)
 │    4. Custom combinations for ungrouped barges (top 10 singles + top 5 pairs)
 │
 ├─ score_and_rank(combinations) -> list[BargeRecommendation]
 │    1. Capacity gate: total_capacity must meet shipment.amount
 │    2. Score each combination (lower = better):
 │         distance_score + (1.0 - cleaning_score) + capacity_score
 │         + AVAILABILITY_SCORE_WEIGHT * availability_score
 │         + VOYAGE_PROGRESS_SCORE_WEIGHT * progress_penalty
 │         - origin_bonus
 │         (availability_score and progress_penalty = 0 when flexible_dates=True;
 │          progress_penalty also 0 when the signal is not prompt)
 │    3. Sort ascending by total_score
 │
 ├─ _populate_tug_info(top N recommendations)
 │    Finds tug from voyage SailingAssets or tow TowAssets
 │
 └─ (called externally by the view/serializer)
      enrich_recommendations()  — attaches carrier, tow, product objects
      add_recommendation_costs() — simulates voyage to estimate costs per leg
```

### Key files

| File | Responsibility |
|------|---------------|
| `webatds/helpers/predictions/simple_equipment_recommendation.py` | Core engine: filtering, combination, scoring, cost enrichment |
| `webatds/helpers/linehaul_utilities.py` | `linehaul_tariffs_for_shipment_request`, `linehaul_carrier_ids_for_shipment_request`, `filter_tariffs_by_barge_attributes` |
| `webatds/helpers/sailing_utilities.py` | `auto_create_voyage(save_to_db=False)` for cost simulation |
| `webatds/helpers/utilities.py` | `estimate_voyage_costs_from_data` for cost calculation from voyage dict |
| `webatds/helpers/routing.py` | `get_shortest_route`, `get_distance_between` for waterway distances |

### Data classes

- **`BargeData`** — one row per candidate barge: barge object, location, distance, capacity, product, carrier/tow/voyage IDs, availability date, voyage-progress penalty
- **`BargeRecommendation`** — one scored combination: barges, group type/ID, scores, barge_locations list, tug, costs/durations (populated later)
- **`RecommendationCosts`** — per-sailing-leg: fuel_cost, day_rate, towing_rate, vendor_cost
- **`RecommendationDurations`** — per-sailing-leg: transit, load, unload, vendor, lock delay, total
- **`RecommendationCleaning`** — prior_product, current_product, cleaning_type

---

## 3. Scoring Model

All score components are normalized to 0–1. **Lower total score = better recommendation.**

### Components

| Component | Formula | What it measures |
|-----------|---------|-----------------|
| Distance | `(avg_dist - min_dist) / dist_range` | Reposition cost proxy — how far the barge is from the shipment origin |
| Cleaning | `1.0 - cleaning_score` | Cargo compatibility — cleaning_score is 0–1 (higher = more compatible), inverted so lower total = better |
| Capacity | `max(0, 1.0 - total_cap / amount)` | Utilization fit — penalizes under-capacity but not over-capacity |
| Availability | `_availability_score(option_available_at)` (0 when `flexible_dates=True`) | Load laycan fit — 0 if on time or early, 0–1 when late (miss laycan). Weight `AVAILABILITY_SCORE_WEIGHT` (0.75). |
| Voyage progress | `_voyage_progress_penalty` (0 when not prompt or `flexible_dates=True`) | Prompt-only readiness from furthest voyage milestone. Weight `VOYAGE_PROGRESS_SCORE_WEIGHT` (0.35). Combos use the worst barge. |
| Origin bonus | subtracted: at-origin / backload (`≤ NEAR_ORIGIN_MILES` = 3) `AT_ORIGIN_SCORE_BONUS` (0.30) only — other proximity relies on `distance_score` | Tips ties; does not fully offset a large cleaning miss |

**Total: `distance_score + (1.0 - cleaning_score) + capacity_score + AVAILABILITY_SCORE_WEIGHT * availability_score + VOYAGE_PROGRESS_SCORE_WEIGHT * progress_penalty - origin_bonus`**

When `flexible_dates=False`, late arrivals are scored with an availability penalty and marked `is_late`. They are **not** hard-excluded — display sort prefers on-time (`is_late` first). **Backloads** (`avg_distance ≤ NEAR_ORIGIN_MILES`) get `BACKLOAD_LATE_GRACE_DAYS` (1) past laycan close before lateness is penalized or marked. When `flexible_dates=True`, availability score is 0.

**Prompt voyage progress** (`PROMPT_LAYCAN_DAYS` = 2): when `earliest_departure` is within 2 days of now, add a 0–1 penalty from Voyage denormalized reported_* FKs (already in the candidate query — no extra ReportedEvent fetch). Not a filter: loading barges stay eligible. On-dock / spotted share the tendered-to-discharge bucket. Tow-only, needs-orders, completed, and discharge-released are 0 (already usable). Non-prompt signals skip this term.

| Furthest milestone | Penalty |
|--------------------|---------|
| No voyage / needs-orders / completed / discharge released | 0.00 |
| Discharge ended | 0.05 |
| Discharge started | 0.15 |
| Tendered to discharge (includes on-dock / spotted) | 0.25 |
| Released loaded / load ended, not yet tendered | 0.70 |
| Still loading or earlier | 1.00 |

Cross-category with **no matrix entry**: same parent family uses `SAME_FAMILY_CLEANING_SCORE` (0.55); otherwise `UNKNOWN_CROSS_CATEGORY_CLEANING_SCORE` (0.20). Parent families are hardcoded in `CATEGORY_PARENT_FAMILY` (e.g. RESIDUAL / NON-RESIDUAL / Crude → BLACK OIL). Start conservative; can loosen after ops feedback.

Shortlist selection uses `select_diverse_shortlist` only when `diversify=true` (default off): reserves ≥1 near-origin option if cleaning is compatible (`cleaning_score > 0`) and the score gap vs the displaced top-N option is ≤ `DIVERSIFY_MAX_SCORE_GAP` (0.5).

API display order (`sort_recommendations_for_display`): `(is_late, total_score, total_voyage_cost)` — on-time first; cost alone cannot promote late options.

### Cleaning score detail

The `_calculate_cleaning_score` method returns 0–1 (higher = better compatibility):

| Condition | Score |
|-----------|-------|
| Same product as shipment | 1.0 |
| MatrixEntry: not_compatible | 0.0 |
| MatrixEntry: cost = 0 | 1.0 |
| MatrixEntry: cost > 0 | `max(0, 1 - (log10(cost) / 5.3)^2)` — e.g. $100→0.86, $1k→0.68, $10k→0.43, $100k→0.11, $200k→0.0 |
| Same product category (fallback) | `CATEGORY_FALLBACK_CLEANING_SCORE` (0.75) |
| Same parent family, different category (fallback) | `SAME_FAMILY_CLEANING_SCORE` (0.55) |
| Unverified prior cargo (`check_prior_cargo=True`) | `CATEGORY_FALLBACK_CLEANING_SCORE` (0.75) |
| Missing product (other cases) | 0.005 |
| Different parent family / unmapped, no matrix entry | `UNKNOWN_CROSS_CATEGORY_CLEANING_SCORE` (0.20) |
| No product on barge | 0.005 |

Cleaning costs are pre-fetched in bulk from `MatrixEntry` and cached in `self.cleaning_costs_cache`.

---

## 4. Business Rules

### Recommendation groups filtering
When `shipment.recommendation_groups` is populated (M2M to `auth.Group`):
- Restricts the barge candidate pool to only barges on tows shared with those groups via `SharedObject`.
- **If recommendation_groups is empty**, no filtering is applied and the full company barge pool is used.
- Barges not on any shared tow are excluded when this filter is active.
- This is an explicit per-signal opt-in; it is NOT auto-derived from the user's groups (which are used for visibility, not recommendation scoping).

### Company 420 category-family hard filter
Gated to `CATEGORY_FAMILY_FILTER_COMPANY_ID` (420). Other companies are unchanged (family is scoring-only).

When the shipment product's category maps to a parent family in `CATEGORY_PARENT_FAMILY`:
- If a voyage candidate has no prior product, use the barge's most recent categorized `SailingAssetProduct` on an earlier current sailing. Not every previous voyage has a `SailingAssetProduct`; empty / uncategorized / outdated sailings are skipped. Lookback only runs when `voyage_id` is set (tow-only candidates are left alone) and only considers sailings whose ETA/arrival is already in the past.
- Drop candidates whose prior-cargo parent family does not match the shipment family.
- A compatible `MatrixEntry` overrides the family gate (barge is kept). `not_compatible` drops the barge even within the same family.
- Barges with still-unknown prior cargo are kept.

Parent families: CLEAN; LUBES (Lubricants/Basestocks, Synthetics); CHEMICALS (Chemicals, Caustic, Pressure, Benzene, Basics, Adhesions, OXO, HCF, OXY); BLACK OIL (Crude, RESIDUAL, NON-RESIDUAL).

### Carrier isolation
Barges are grouped by `carrier_id`. Carriers generally do not move each other's barges, so all barges in a recommendation share the same carrier.

### Linehaul filtering
When `only_active_voyages=True` and `shipment.product` is set:
1. Find carrier IDs with matching linehaul towing tariffs via `linehaul_carrier_ids_for_shipment_request` (filters by product, product category, date, loaded status, unit).
2. Exclude linehaul voyage barges whose carrier is set and is NOT in the matching list.
3. Linehaul voyages with a null carrier pass through (they are acceptable as long as a rate exists).
4. If `shipment.product` is `None`, skip linehaul filtering entirely.

### Barge location resolution
Priority for determining where a barge will be:
1. **Voyage final port** (`voyage.end_port`) — used when the voyage exists and does NOT need orders (where the barge will be free after the committed trip).
2. **Needs-orders** — current location if set. If location is missing, voyage `end_port`, unless `latest_status.ETA` is more than `NEEDS_ORDERS_END_PORT_ETA_SANITY_DAYS` (15) out (faulty far-coast match) — then voyage `start_port`.
3. **Tow fleeting port** — used for barges on tows without voyages.
4. **Barge.location** — ultimate fallback.

### Laycan idle time (`laycan_firm=True`)
When the `laycan_firm` query param is `true`, `add_recommendation_costs` computes idle gaps between the simulated voyage and the shipment's laycan windows and includes them in costs and durations:

- **Load idle**: gap between the barge's estimated arrival at the load port and `shipment.earliest_departure`. Computed inside `estimate_voyage_costs_from_data` (in `utilities.py`) using the voyage-simulated reposition leg timing — reposition arrival from the leg before the first `start_stop_type=LOAD`, or `barge_date_available` when already at load. Note: `auto_create_voyage` resets `start_date` per order from `order["latest_departure"]`, so the idle gap is not visible in the voyage simulation itself and must be computed separately.
- **Discharge idle**: gap between the simulated discharge arrival and `shipment.earliest_arrival`, when set.
- Idle durations are computed and injected inside `estimate_voyage_costs_from_data` (pass `load_laycan_open`, `discharge_laycan_open`, `barge_date_available`). The idle time is added to the load leg's `time_in_start_port` / last leg's `time_in_end_port` so day rates and idle fuel are naturally charged over the full waiting period.
- `load_idle_*` is attached to the first `start_stop_type=LOAD` duration/cost entry (not the final interchange leg). `discharge_idle_*` is attached to the last leg.
- When `laycan_firm=False` (default), `None` is passed for all laycan params and idle fields are `None`.

### Linehaul laycan window (`LINEHAUL_STALE_HOURS`, 72 h)
- Excludes linehaul voyage recommendations in `score_and_rank` when load laycan (`earliest_departure`) opens more than `linehaul_stale_hours` after the barge's estimated `date_available`.
- Skipped when the barge's voyage term tow has `exclude_availability_time_bar=True`.
- Defaults to `LINEHAUL_STALE_HOURS`; override via API query param `linehaul_stale_hours`.

### Availability
- A barge is excluded if it is on a committed voyage (not needs_orders) that overlaps with `load_date ± 3 days`.
- Completed voyages (`time_completed` set) do not block availability, even if schedule dates still overlap the laycan window.
- A voyage with `reported_discharge_release` and only one discharge leg also does not block availability. Multiple discharge legs (even at the same port) still block until the voyage is completed.
- The availability date depends on voyage load/discharge status:
  - **Needs-orders**: `now` (they can depart for the signal load immediately). Time to load is now + transit from the resolved location (location, else end port, else start port if the end-port ETA looks like a bad match).
  - **Not loaded** (all of `reported_load_start`, `reported_load_end`, `reported_load_release` are null) **and `latest_arrival` is in the future**: use `voyage.latest_arrival`.
  - **Not loaded but `latest_arrival` is in the past** (stale scheduled date): use ETA branch (see below).
  - **Loaded** (any load event exists): use ETA branch (see below).
  - **ETA branch**: `voyage.latest_status.ETA` (preferred). If missing, `latest_departure` plus average loaded transit (last 30 days if at least 4 samples; otherwise `select_historical_sample` same-month seasonal, then 365-day lookback). If no historical duration, `voyage.latest_arrival`. If none of `reported_discharge_start`, `reported_discharge_end`, `reported_discharge_release` are set (barge hasn't started discharging yet), add `subservice.time_in_end_port` to account for remaining discharge time.

### Product type compatibility
- Liquid products → tank barge classes only (`Barge.tank_barge_classes()`)
- Dry products → dry barge classes only (`Barge.dry_barge_classes()`)
- No product on shipment → no filtering

### Tug association
- For voyage groups: tug found via `SailingAsset` on the voyage with `asset__tug__isnull=False`
- For tow groups: tug found via `TowAsset` on the tow with `asset__tug__isnull=False`
- **TBN fallback**: if no tug is found on the group, `_find_last_tug_for_barges` queries the most recent voyage the barges sailed on that had a tug. `tug_is_tbn` is set to `True` to indicate the tug is a suggestion from history, not the assigned tug.

### Prior product resolution
- **Voyage barges** (priority order):
  1. `SailingAssetProduct` M2M (via `sailing_asset=OuterRef("pk")`, `order_by("-id")` for latest) — the preferred source, automatically scoped to the current sailing by the outer query's filters.
  2. `SailingAsset.product` FK — legacy fallback for sailing assets not yet migrated to M2M.
  3. When the current voyage has no product, set `check_prior_cargo=True`, expose `prior_product_commodity_title` for display, and use `CATEGORY_FALLBACK_CLEANING_SCORE` (0.75). Other missing-product cases keep the default fallback score (0.005).
  4. No barge-level fallback — avoids showing stale/unrelated products from the barge model.
- **Tow-only barges** (no voyage): uses `Barge.product` via `_get_product_ids` as the only available source.

### Rate priority for cost estimation
1. Tow contracted rate (`tow.contract.contracted_barge_day_rate` / `contracted_tug_day_rate`)
2. SailingAsset rate from the voyage
3. Asset default day rate (`barge.day_rate` / `tug.day_rate`)

---

## 5. Cost Estimation

Cost estimation is a **post-scoring enrichment step** run on the top N recommendations via `add_recommendation_costs()`.

### Process
1. Calculate the shipment route once (`routing.get_shortest_route`).
2. For each recommendation:
   - Determine if the barge is already at origin (port ID match or distance ≤ `NEAR_ORIGIN_MILES` = 3).
   - If not at origin: build a **reposition order** (barge location → shipment start_port) + **shipment order**.
   - If at origin: only the shipment order.
   - Call `sailing_utilities.auto_create_voyage(save_to_db=False)` to simulate voyage structure.
   - Call `utilities.estimate_voyage_costs_from_data()` to calculate costs from the simulated voyage.
   - Look up cleaning info from `MatrixEntry`.

### Cost components (per sailing leg)

| Component | Service type | Source |
|-----------|-------------|--------|
| `fuel_cost` | Dedicated | Transit + idle fuel burn × price per gallon |
| `day_rate` | Both | Sum of (asset day_rate × quantity × total_days) |
| `towing_rate` | Linehaul | From towing tariff rate data |
| `vendor_cost` | Both | Third-party service costs. `get_default_misc_costs_for_sailing` keeps only **cleaning** at an `ON_HIRE` start port (barge is assumed to leave immediately). Load/discharge vendors are unchanged. Reposition `time_in_start_port` also defaults to 0 for `ON_HIRE` legs. |
| `cleaning_cost` | Both | From MatrixEntry lookup (top-level, not per-leg) |

**`total_voyage_cost`** = sum of all leg costs + cleaning_cost.

### Duration components (per sailing leg)
- `transit_duration`, `load_duration`, `unload_duration`
- `vendor_duration_start`, `vendor_duration_end`
- `lock_delay_duration`, `total_duration`

---

## 6. Known Limitations

| Area | Limitation |
|------|-----------|
| Scoring weights | Distance, cleaning, capacity at 1.0; availability at `AVAILABILITY_SCORE_WEIGHT` (0.75); voyage progress at `VOYAGE_PROGRESS_SCORE_WEIGHT` (0.35) on prompt signals. `flexible_dates=True` omits availability and progress. |
| Tug matching | TBN fallback finds last tug used by barges; no independent tug recommendation by proximity/carrier yet |
| Carrier intelligence | No speed or reliability data used in scoring |
| Fleet awareness | No consideration of other pending/scheduled shipments |
| Availability window | Fixed ±3 days, not adjusted for shipment urgency or load date distance |
| Custom combinations | Simple heuristic: top 10 singles + top 5 pairs by distance |
| Voyage progress | Prompt signals use denormalized discharge milestones; on-dock/spotted are not distinct; non-prompt signals still use date_available only |
| Idle time | No optimization to minimize idle time between voyages |
| Over-capacity penalty | No penalty for recommending a 30k bbl barge for a 10k bbl shipment |
| Batch scheduling | Single-shipment optimization only |
| Backload via `avg_distance` | At-origin bonus and late grace use mean combo distance, while lateness uses the latest barge arrival. A near+far pair can look like a backload even when one barge is still far. Accepted for now — we are not optimizing single-barge / mixed-distance pairings. |

---

## 7. Enhancement Roadmap

### Phase 1 — Scoring Improvements (Near-term)

- **Configurable scoring weights**: Allow tuning the relative importance of distance, cleaning, capacity, and rate via parameters or configuration.
- **Rate-aware scoring**: Incorporate towing rate / estimated voyage cost into the ranking score (currently only used in post-scoring enrichment, not in the ranking itself).
- **Over-capacity penalty**: Add a capacity score component that penalizes excessive over-capacity (prefer a 10k bbl barge for a 10k bbl shipment over a 30k bbl barge).
- **Tug matching**: When a group has no tug, find the nearest available tug owned by the same carrier. Consider tug availability, location, and BHP requirements.
- **Dynamic availability window**: Scale the ±3 day window based on how far out the load date is and shipment urgency.
- **Market recommendations**: When no viable recommendations exist or all top recommendations have costs significantly above historical norms, surface a suggestion to request new quotes from carriers. This helps dispatchers act quickly when the available fleet cannot cover a signal at a reasonable rate.
- **Fleeting / layup cost awareness**: Factor in the cost of keeping barges idle at fleeting ports between voyages when deciding whether to move a barge now or wait.
- **Customer preferences**: Some customers may prefer or reject certain carriers or specific barges. Add customer-level filtering to exclude disallowed assets or boost preferred ones.

### Phase 2 — Intelligence Layer (Medium-term)

- **Carrier speed**: Use historical transit time data (connects to `transit_time_estimator.py` already in predictions/) to estimate delivery time per carrier.
- **Carrier reliability**: Score carriers by on-time delivery rate, breakdown frequency, and historical performance.
- **Voyage progress awareness**: Prompt signals already prefer barges further along in discharge. Remaining: on-dock/spotted as a distinct tier, and using progress on non-prompt signals if ETAs stay unreliable.
- **Idle time optimization**: Minimize barge idle time between the end of the current voyage and the start of the recommended shipment.
- **Signal-aware scheduling**: Consider other pending shipment requests to avoid recommending barges already earmarked for higher-priority shipments.
- **Equipment-type recommendations**: Instead of always recommending specific named assets, support a mode that outputs the number and type of equipment needed (e.g. "2 x 10k bbl tank barges + 1 tug"). This covers cases where the user cannot select specific assets and only needs to know what class/quantity to request from a carrier.
- **Regulatory / inspection windows**: Check for upcoming COI (Certificate of Inspection) expirations, hull surveys, or required maintenance that would take a barge out of service during the shipment window.
- **Demurrage risk**: Factor in the risk of delays and potential demurrage charges at load/discharge ports when a recommended barge is cutting it close on timing.
- **Backhaul / return positioning**: After delivering, the barge needs to go somewhere. Prefer barges whose post-delivery position is near the origin of another pending signal, reducing empty repositioning.

### Phase 3 — Batch Optimization and Blue Water (Long-term)

- **Multi-shipment optimization**: Given N shipment requests and M available assets, find the globally optimal assignment that minimizes total fleet cost.
- **Fleet-level scheduling**: Balance scheduling across all pending shipments to maximize fleet utilization.
- **Approach options**: Constraint satisfaction, linear programming (e.g. PuLP/OR-Tools), or heuristic assignment algorithms.
- **Considerations**: Shared carriers across shipments, waterway congestion, scheduling conflicts, depot/fleet positioning, carrier capacity limits.
- **Blue water vessel support**: Extend the asset pool to include ocean-going ships with their own capacity models (DWT, TEU), speed profiles, draft constraints, and rate structures. This will require generalizing the `BargeData` / `BargeRecommendation` data classes and the combination/scoring logic to be asset-type agnostic.
- **User feedback loop**: Learn from which recommendations dispatchers accept vs reject to improve scoring weights over time.
- **Draft / water level constraints**: Factor in barge draft limits and waterway depths that vary by season. A fully loaded barge may not be able to transit shallow stretches on certain routes.

---

## 8. Testing

### Test file
`webatds/tests/test_simple_equipment_recommendation.py`

### Test patterns
- Uses `CustomTestCase` with `base_db.json` fixtures
- Creates real DB objects in `setUpTestData`: company, products, ports, barges, tugs, carriers, voyages, tows
- Mocks external dependencies (e.g. `linehaul_carrier_ids_for_shipment_request`) with `unittest.mock.patch`
- Tests cover: filtering, scoring, cleaning matrix, grouping, enrichment, cost/duration calculation, edge cases

### Key test areas

| Test area | What it validates |
|-----------|------------------|
| `test_main_function_with_real_data` | End-to-end pipeline runs without error |
| `test_capacity_calculation_*` | Liquid → tank_capacity, dry → tonnage_capacity |
| `test_cleaning_score_*` | Product match = 1.0, category match = 0.75, matrix cost curve, not_compatible = 0.0 |
| `test_group_determination_*` | Voyage group, tow group, custom group detection |
| `test_only_valid_linehaul_carrier_barges_included` | Linehaul filtering excludes invalid carriers |
| `test_filter_active_voyages_*` | Tracking-enabled voyages included, inactive excluded |
| `test_cleaning_matrix_cost_scale` | Logarithmic cost curve at $0, $100, $1k, $10k, $100k, $200k |
| `test_enrich_recommendations_*` | Prior product resolution, carrier/tow/voyage attachment |
| `test_get_cleaning_info_*` | Matrix entry lookup, same product, no product, no entry |
| `test_calculate_durations_per_sailing_*` | Duration extraction from voyage simulation data |
| `CategoryFamilyHardFilterTests` | Company 420 family hard-filter, matrix override, previous-voyage lookback |
| `VoyageProgressPenaltyTests` / prompt ranking | Milestone buckets, prompt vs non-prompt / flexible_dates, worst-barge combo |

### Running tests
```bash
python manage.py test webatds.tests.test_simple_equipment_recommendation --noinput
```

---

## 9. Rules for AI Agents

When working on the recommendation algorithm:

1. **Read this document first** before making changes.
2. **Follow existing patterns** — the engine uses a pipeline of filter → combine → score → enrich. New features should fit into this pipeline.
3. **Keep scoring normalized** — all score components should be 0–1 scale. Document any new components here.
4. **Preserve carrier isolation** — this is a fundamental business rule. Any combination must respect it.
5. **Test with real data patterns** — use the existing test patterns with `CustomTestCase` and `setUpTestData`. Mock external services, not internal logic.
6. **Update this document** when adding new scoring components, business rules, or pipeline steps.
7. **Performance matters** — the engine uses bulk queries and caching (e.g. `cleaning_costs_cache`, `values_list` with `.distinct()`). Avoid N+1 query patterns.
8. **Cost estimation is separate from scoring** — `add_recommendation_costs` runs post-scoring on top N only. If you want cost to influence ranking, add it as a score component in `score_and_rank`, not by reordering after cost enrichment.
