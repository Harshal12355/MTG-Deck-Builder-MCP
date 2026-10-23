# Live ETA Calculation

## Overview

The ETA system predicts when a vessel will arrive at its next port (load or discharge). It runs on two triggers:

1. **Automatic position reports** -- a periodic task that pulls AIS tracks, classifies events, and computes ETA for active voyages.
2. **Status log ETA recalculation** -- called when a status log is updated or created to refresh the ETA from the vessel's last known position.

## Call Chain

```text
automatic_position_report_by_voyage (dpr_helpers.py)
  -> _automatic_position_report_by_voyage
       -> parse_events (ais_helper.py)
            -> get_distance_from_destination (ais_helper.py)
                 -> get_eta_to_destination (sailing_utilities.py)
                      -> determine_ports_reached (sailing_utilities.py)
                      -> has_port_been_reached (sailing_utilities.py)
                      -> _build_combined_route
                      -> _calculate_port_time
                      -> get_route_duration

recalculate_status_log_eta (dpr_helpers.py)
  -> get_distance_from_destination (ais_helper.py)
       -> get_eta_to_destination (sailing_utilities.py)
            -> (same chain as above)

sailing_position_report (sailing_utilities.py)
  -> get_eta_to_destination (sailing_utilities.py)
       -> (same chain as above)
```

## Asset Selection and Track Sources

Before ETA can be calculated, the system must resolve **which asset to track** and **where its position data comes from**. This is handled by `get_first_trackable_asset` and `get_asset_historicals`.

### `get_first_trackable_asset`

**File:** `webatds/helpers/utilities.py`

Picks the single asset whose position will drive the ETA. Priority order (when `include_barges=True`, which is the default for position reports):

1. **Barge with GPS** -- a barge that has `track_vessel=True`, is not on outcharter, and has a `tracking_device`, OR a barge the company has access to (e.g., a shipper barge shared via carrier permission). Among qualifying barges, the one with the most recent `gps_time_located` wins.
2. **Tug** -- a tug with AIS (`mmsi`).
3. **Ship** -- a ship with AIS.
4. **Fallback barge** -- if nothing else is trackable, the last barge on the voyage.

### `get_asset_historicals`

**File:** `webatds/helpers/dpr_helpers.py`

Fetches the position track for the selected asset:

- **Tug or Ship (AIS):** calls `get_ais_history` with the asset's MMSI to fetch AIS positions from the database or external API.
- **Barge (GPS + implied):** calls `get_combined_barge_tracks_with_permissions`, which:
  1. Checks if the barge has a `tracking_device` and whether the company has GPS access (owner or via permission window).
  2. Within the access window: fetches real GPS tracks from `barge_track_history`.
  3. Outside the access window: fetches implied tracks (BargeTrack records from voyages, emails, etc.).
  4. Combines both into a single chronological track list.

This means **barge GPS tracks feed directly into the ETA pipeline** when the barge is the tracked asset -- for example, when there is no tug on the voyage, or when the barge has GPS and is prioritized.

## Key Functions

### `automatic_position_report_by_voyage` / `_automatic_position_report_by_voyage`

**File:** `webatds/helpers/dpr_helpers.py`

Entry point for the periodic position report pipeline. Acquires a cache lock per voyage to prevent concurrent runs.

1. Resolves the active subservice and tracked asset via `get_first_trackable_asset` (prefers GPS barges, then tugs, then ships).
2. Fetches position tracks via `get_asset_historicals` (AIS for tugs/ships, GPS + implied tracks for barges).
3. Calls `parse_events` with `load_events` and `discharge_events` from the voyage.
4. Merges and classifies events, then writes status logs.

### `parse_events`

**File:** `webatds/helpers/ais_helper.py`

Iterates over AIS events and, for each event, calls `get_distance_from_destination` to compute ETA and distance. It forwards `load_events` and `discharge_events` through to that function. These events are critical for determining which port the vessel is heading toward.

### `get_distance_from_destination`

**File:** `webatds/helpers/ais_helper.py`

Dispatcher that handles two cases:

- **No selected route:** computes straight-line distance and simple speed-based ETA.
- **With selected route:** delegates to `get_eta_to_destination` in `sailing_utilities.py`, passing `load_events` and `discharge_events` through.

### `get_eta_to_destination`

**File:** `webatds/helpers/sailing_utilities.py`

The core ETA function. Steps:

1. **Get future subservices** -- all uncompleted subservices from the current one onward.
2. **Filter to next load/discharge** -- if `to_next_load_or_discharge=True`, truncates to the next subservice whose `end_stop_type` is LOAD or DISCHARGE.
3. **Build combined route** -- merges selected routes from future subservices into one route.
4. **Route remainder** -- computes the remaining portion of the combined route from the vessel's current position.
5. **Determine ports reached** -- calls `determine_ports_reached` to decide if the start (origin/load) and end (destination/discharge) ports have been reached.
6. **Reroute to origin if needed** -- if the start port has NOT been reached and we are calculating to next load/discharge, reroutes the ETA toward the origin port instead of the destination.
7. **Calculate port time** -- adds time-in-port and vendor service durations.
8. **Weather and lock delays** -- adds delays from `get_route_duration`.
9. **Scheduled boat pickup** -- calls `_get_scheduled_boat_pickup_delays` to add the travel time from the scheduled boat to the barge (skipped when a tug is already assigned).
10. **Return** -- dict with `eta`, `remaining_duration`, `remaining_idle_duration`, `weather_delay`, `route_data`, `destination_subservice`, `eta_to_origin`, and `scheduled_boat_pickup_duration`.

### `determine_ports_reached`

**File:** `webatds/helpers/sailing_utilities.py`

Isolated helper that decides `(start_reached, end_reached)`. Three code paths based on voyage type:

**Bunker voyages** (BUNKER_LOAD, BUNKER_DELIVERY, BUNKER_TANK_DISCHARGE):
- `start_reached` is always `True` (origin always considered reached).
- For BUNKER_LOAD the load port is the END port, so `load_events` are used for `end_reached`.
- For BUNKER_DELIVERY / BUNKER_TANK_DISCHARGE, `discharge_events` are used for `end_reached`.

**Standard voyages (single port):**
- `load_events` drive `start_reached`, `discharge_events` drive `end_reached`.
- Events are passed through unscoped.
- `start_reached` is also forced `True` when `voyage.company.always_calculate_eta_to_destination` is set (see below).

**Standard voyages (multi-port):**
- Uses `voyage.is_multi_load_port()` / `voyage.is_multi_discharge_port()` to detect multiple distinct load or discharge ports across current subservices.
- When multiple ports exist, events are scoped to the current subservice via `Q(subservice=current_subservice) | Q(subservice__isnull=True)` to prevent a load event at Port A from falsely marking Port B as reached.

### `always_calculate_eta_to_destination` (Company flag)

**Field:** `Company.always_calculate_eta_to_destination` (BooleanField, default `False`)

When `True`, `start_reached` is always considered `True` in `determine_ports_reached` for standard voyages, so the ETA is always calculated toward the destination rather than rerouting to the origin. This is used for dry cargo companies or companies that buy barges already loaded -- in these cases, there may never be a reported event indicating the barge reached the origin, so the system should skip the "ETA to origin" phase entirely.

### `_get_scheduled_boat_pickup_delays`

**File:** `webatds/helpers/sailing_utilities.py`

Computes the travel time for a scheduled boat (`Voyage.scheduled_boat`) to reach the barge when there is no current tug on the active subservice. Called from `get_eta_to_destination`.

1. Short-circuits if no `scheduled_boat`, a `tug` is already assigned, or the boat has no location.
2. Resolves the barge with the most recent `time_located` from the subservice's sailing assets.
3. Computes speed using `avg_transit_speed` (historical AIS), falling back to `speed_light`, `estimated_speed`, or 4 mph.
4. Builds a route from the scheduled boat's location to the barge via `format_route_data`.
5. Returns `(duration, weather_delay, lock_delay)` or `(None, 0, 0)` if pickup cannot be computed.
6. Wrapped in try/except so a failure never breaks the main ETA.

The returned `duration` is added to `remaining_duration` in `get_eta_to_destination`, and the return dict exposes `scheduled_boat_pickup_duration` so consumers can display how much of the ETA is the boat traveling to the barge.

### `has_port_been_reached`

**File:** `webatds/helpers/sailing_utilities.py`

Returns `True` if any of these conditions hold:
1. The vessel is within the port's geofence (via `is_within_port_geofence`).
2. Relevant reported events exist (load or discharge events passed in).
3. A subservice timestamp field is set (e.g., `actual_origin_arrival` or `time_completed`).

### `recalculate_status_log_eta`

**File:** `webatds/helpers/dpr_helpers.py`

Called when a status log needs its ETA refreshed (e.g., after a status log update). Uses the voyage's latest status log location and passes `voyage.load_events()` / `voyage.discharge_events()` through to `get_distance_from_destination`.

### `sailing_position_report`

**File:** `webatds/helpers/sailing_utilities.py`

Called for on-demand position reports (e.g., from the UI). Calls `get_eta_to_destination` directly with the voyage's load and discharge events.

## Voyage Model Helpers

**File:** `webatds/models.py` (on the `Voyage` model)

| Method | Purpose |
|---|---|
| `load_events(**kwargs)` | Returns `ReportedEvent` queryset filtered to `ALL_LOAD_EVENTS` for this voyage |
| `discharge_events(**kwargs)` | Returns `ReportedEvent` queryset filtered to `ALL_DISCHARGE_EVENTS` for this voyage |
| `is_multi_load_port()` | `True` if current subservices have more than one distinct `start_port` with `start_stop_type=LOAD` |
| `is_multi_discharge_port()` | `True` if current subservices have more than one distinct `end_port` with `end_stop_type=DISCHARGE` |

## Important Rules

- **Always pass load/discharge events** when calling `get_distance_from_destination` or `get_eta_to_destination`. Without them, the system falls back to geofence-only detection which can show ETA to the wrong port.
- **Bunker voyage types** have reversed or simplified port semantics -- `determine_ports_reached` handles this. Do not add special bunker logic elsewhere.
- **Multi-port scoping** is handled inside `determine_ports_reached`. Callers should pass unscoped `voyage.load_events()` / `voyage.discharge_events()` and let the helper scope as needed.
- **`eta_to_origin`** in the return dict indicates the ETA is toward the origin port (start not yet reached), not the destination. Consumers should check this flag to display the correct label.
- **Scheduled boat pickup** is handled inside `get_eta_to_destination`. Callers pass `scheduled_boat=voyage.scheduled_boat` and `tug=tug` (the resolved tug from the subservice). Do not add scheduled-boat logic in callers.

## Future Roadmap

- ~~**Scheduled boat ETA projection** -- implemented.~~ See `_get_scheduled_boat_pickup_delays` above.

## File Locations

| File | Role |
|---|---|
| `webatds/helpers/sailing_utilities.py` | `get_eta_to_destination`, `_get_scheduled_boat_pickup_delays`, `determine_ports_reached`, `has_port_been_reached`, `sailing_position_report` |
| `webatds/helpers/ais_helper.py` | `parse_events`, `get_distance_from_destination` |
| `webatds/helpers/dpr_helpers.py` | `automatic_position_report_by_voyage`, `recalculate_status_log_eta` |
| `webatds/models.py` | `Voyage.load_events()`, `Voyage.discharge_events()`, `Voyage.is_multi_load_port()`, `Voyage.is_multi_discharge_port()` |
