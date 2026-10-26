"""Multi-deck Rule 0 pod balance."""

from __future__ import annotations

from typing import Any

def evaluate_pod(seats: list[dict[str, Any]]) -> dict[str, Any]:
    """Compare 2-4 analyzed decks for Rule 0 table balance (EDHcheck Pod Checker)."""
    brackets = [s["analysis"]["bracket"]["bracket"] for s in seats]
    powers = [s["analysis"]["power_score"]["total"] for s in seats]
    speeds = [s["analysis"]["power_score"]["speed"] for s in seats]

    b_spread = max(brackets) - min(brackets) if brackets else 0
    p_spread = round(max(powers) - min(powers), 1) if powers else 0.0
    s_spread = round(max(speeds) - min(speeds), 1) if speeds else 0.0
    p_avg = sum(powers) / len(powers) if powers else 0.0
    b_max, b_min = max(brackets, default=0), min(brackets, default=0)

    outliers: list[dict[str, Any]] = []
    for s in seats:
        b = s["analysis"]["bracket"]["bracket"]
        p = s["analysis"]["power_score"]["total"]
        if b_spread >= 2 and b == b_max and brackets.count(b_max) == 1:
            outliers.append({"seat": s["name"], "direction": "above", "reason": f"Bracket {b} against a pod of Bracket {b_min}–{max(x for x in brackets if x != b_max)}"})
        elif b_spread >= 2 and b == b_min and brackets.count(b_min) == 1:
            outliers.append({"seat": s["name"], "direction": "below", "reason": f"Bracket {b} against a pod of Bracket {min(x for x in brackets if x != b_min)}+"})
        elif b_spread <= 1 and p_spread >= 2.0 and p - p_avg >= 1.2:
            outliers.append({"seat": s["name"], "direction": "above", "reason": f"Power {p:.1f} against a pod average of {p_avg:.1f}"})

    if b_spread >= 2:
        verdict = "mismatched"
        headline = "Mismatched pod"
        detail = f"These decks are {b_spread} brackets apart. The lower-bracket decks are unlikely to interact with what the higher-bracket deck is doing."
    elif b_spread == 1 and p_spread >= 2.5:
        verdict = "uneven"
        headline = "Uneven pod"
        detail = f"One bracket apart with a {p_spread:.1f}-point power gap. Expect the top deck to draw table attention early."
    elif b_spread == 1 or p_spread >= 1.5:
        verdict = "slight"
        headline = "Close pod, slight edge"
        detail = f"Within one bracket and a {p_spread:.1f}-point power spread. Competitive games with a mild favourite."
    else:
        verdict = "balanced"
        headline = "Balanced pod"
        detail = f"Same bracket, {p_spread:.1f} points between strongest and weakest. Built for the same game."

    if s_spread >= 3.0:
        detail += f" Speed varies noticeably ({s_spread:.1f} points), so one deck sets the clock."

    seat_summaries = []
    for s in seats:
        a = s["analysis"]
        flags = a["bracket"]["flags"]
        notes: list[str] = []
        if flags["game_changers"]:
            notes.append(f"{len(flags['game_changers'])} Game Changer(s): {', '.join(flags['game_changers'])}")
        if flags["two_card_combos"]:
            notes.append(f"{len(flags['two_card_combos'])} two-card combo(s)")
        if flags["early_two_card_combo"]:
            notes.append("early combo potential")
        tutors = a["roles"]["counts"].get("tutor", 0)
        if tutors >= 5:
            notes.append(f"{tutors} tutors")
        if flags["fast_mana"]:
            notes.append(f"{len(flags['fast_mana'])} fast mana")
        if flags["extra_turns"]:
            notes.append(f"{len(flags['extra_turns'])} extra turns")
        if flags["mass_land_denial"]:
            notes.append(f"mass land denial ({', '.join(flags['mass_land_denial'])})")
        seat_summaries.append({
            "seat": s["name"],
            "commanders": a["commanders"],
            "bracket": a["bracket"]["bracket"],
            "bracket_label": a["bracket"]["label"],
            "power_score": a["power_score"]["total"],
            "speed_score": a["power_score"]["speed"],
            "consistency_score": a["power_score"]["consistency"],
            "median_commander_turn": s.get("median_commander_turn"),
            "rule_zero_notes": notes,
        })

    return {
        "verdict": verdict,
        "headline": headline,
        "detail": detail,
        "bracket_spread": b_spread,
        "power_spread": p_spread,
        "speed_spread": s_spread,
        "outliers": outliers,
        "seats": seat_summaries,
    }
