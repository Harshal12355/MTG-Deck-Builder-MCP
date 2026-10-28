"""WotC bracket, power score, school score, and synergy."""

from __future__ import annotations

import re
from collections import Counter
from typing import Any

from ..scryfall import front_type_line, oracle_text
from ._card_utils import _front_lower

# Official WotC Game Changers list (53 cards, Feb 9 2026 update) fallback when Scryfall flag is absent.
GAME_CHANGERS_SET: frozenset[str] = frozenset(
    name.lower()
    for name in (
        "Ad Nauseam", "Ancient Tomb", "Aura Shards", "Biorhythm", "Bolas's Citadel",
        "Braids, Cabal Minion", "Chrome Mox", "Coalition Victory", "Consecrated Sphinx", "Crop Rotation",
        "Cyclonic Rift", "Demonic Tutor", "Drannith Magistrate", "Enlightened Tutor", "Farewell",
        "Field of the Dead", "Fierce Guardianship", "Force of Will", "Gaea's Cradle", "Gamble",
        "Gifts Ungiven", "Glacial Chasm", "Grand Arbiter Augustin IV", "Grim Monolith", "Humility",
        "Imperial Seal", "Intuition", "Jeska's Will", "Lion's Eye Diamond", "Mana Vault",
        "Mishra's Workshop", "Mox Diamond", "Mystical Tutor", "Narset, Parter of Veils", "Natural Order",
        "Necropotence", "Notion Thief", "Opposition Agent", "Orcish Bowmasters", "Panoptic Mirror",
        "Rhystic Study", "Seedborn Muse", "Serra's Sanctum", "Smothering Tithe", "Survival of the Fittest",
        "Teferi's Protection", "Tergrid, God of Fright", "Thassa's Oracle", "The One Ring",
        "The Tabernacle at Pendrell Vale", "Underworld Breach", "Vampiric Tutor", "Worldly Tutor",
    )
)

FAST_MANA_SET: frozenset[str] = frozenset(
    name.lower()
    for name in (
        "Sol Ring", "Mana Crypt", "Mana Vault", "Grim Monolith", "Mox Diamond", "Chrome Mox",
        "Mox Opal", "Jeweled Lotus", "Lotus Petal", "Dark Ritual", "Cabal Ritual", "Seething Song",
        "Elvish Spirit Guide", "Simian Spirit Guide", "Rite of Flame", "Pyretic Ritual",
        "Desperate Ritual", "Ancient Tomb", "City of Traitors",
    )
)

EXTRA_TURN_SET: frozenset[str] = frozenset(
    name.lower()
    for name in (
        "Time Walk", "Time Warp", "Temporal Manipulation", "Time Stretch", "Temporal Mastery",
        "Nexus of Fate", "Beacon of Tomorrows", "Capture of Jingzhou", "Karn's Temporal Sundering",
        "Magistrate's Scepter", "Part the Waterveil", "Alrund's Epiphany", "Expropriate",
        "Temporal Trespass", "Walk the Aeons", "Emrakul, the Promised End", "Ugin's Nexus",
        "Savor the Moment", "Medomai the Ageless", "Lighthouse Chronologist", "Teferi, Master of Time",
        "Seedtime",
    )
)

MLD_SET: frozenset[str] = frozenset(
    name.lower()
    for name in (
        "Armageddon", "Ravages of War", "Jokulhaups", "Obliterate", "Decree of Annihilation",
        "Catastrophe", "Boom // Bust", "Sunder", "Mana Vortex", "Land Equilibrium", "Wildfire",
        "Burning Sands", "Keldon Firebombers", "Impending Disaster", "Ruination", "Price of Glory",
        "Thoughts of Ruin", "Devastation", "Cataclysm", "Winter Orb", "Static Orb", "Stasis",
        "Blood Moon", "Back to Basics", "Vorinclex, Voice of Hunger",
    )
)

FREE_SPELL_SET: frozenset[str] = frozenset(
    name.lower()
    for name in (
        "Force of Will", "Force of Negation", "Fierce Guardianship", "Deflecting Swat",
        "Deadly Rollick", "Flawless Maneuver", "Force of Vigor", "Pact of Negation",
        "Slaughter Pact", "Summoner's Pact", "Mental Misstep", "Mindbreak Trap",
        "Foil", "Daze", "Gush", "Gitaxian Probe", "Snuff Out", "Submerge", "Misdirection",
        "Commandeer", "Pyrokinesis", "Contagion", "Endurance", "Solitude", "Subtlety", "Grief", "Fury",
    )
)

# Official WotC Oct 2025 minimum turns expected before a game ends.
BRACKET_EXPECTED_TURNS: dict[int, str] = {
    1: "9+ turns (theme/showcase over winning)",
    2: "8+ turns (incremental, telegraphed board wins)",
    3: "6+ turns (wins Turn 7+; 1-turn wins from accrued resources)",
    4: "4+ turns (wins Turn 5–6; fast mana, tutors, sudden combo wins)",
    5: "Any turn (Turns 1–4 cEDH tournament metagame)",
}

# Commanders whose command-zone text is half of a compact 1- or 2-card infinite or Turn 3-4 storm win.
NATURAL_B4_COMMANDERS: dict[str, str] = {
    "celes, rune knight": "Natural Bracket 4 combo commander (+1/+1 counter on graveyard entry erases Persist -1/-1 counters for 1-card Murderous Redcap / Persist loops; a smooth Bracket 3 build must use ETB Domino Reanimator chains instead of big vanilla bricks).",
    "stella lee, wild card": "Natural Bracket 4 combo commander (taps on spell #3 to copy any 1-mana untap cantrip like Cerulean Wisps for a 1-card infinite).",
    "the jolly balloon man": "Natural Bracket 4 combo commander (3-MV haste cloner goes infinite with any untap creature like Village Bell-Ringer or Coercive Recruiter).",
    "rowan, scion of war": "Natural Bracket 4 storm commander (tap discounts all B/R spells this turn by life lost for Turn 3–4 X-spell kills).",
    "will, scion of peace": "Natural Bracket 4 storm commander (tap discounts all W/U spells this turn by life gained).",
    "zirda, the dawnwaker": "Natural Bracket 4 combo commander (reduces activated ability costs by {2}, going infinite with Basalt Monolith or Grim Monolith).",
    "kinnan, bonder prodigy": "Natural Bracket 4/5 mana engine (doubles nonland mana and goes infinite with Basalt Monolith).",
    "malcolm, keen-eyed navigator": "Natural Bracket 4/5 combo commander (1-card infinite with Glint-Horn Buccaneer).",
    "godo, bandit warlord": "Natural Bracket 4/5 1-card combo commander (tutors and equips Helm of the Host by himself).",
    "najeela, the blade-blossom": "Natural Bracket 4/5 combat-combo commander (1-card infinite combat phases with Derevi or Druids' Repository).",
    "winota, joiner of forces": "Natural Bracket 4 snowball stax/combat commander.",
    "yuriko, the tiger's shadow": "Natural Bracket 4 tempo commander (commander ninjutsu dodges commander tax permanently).",
    "urza, lord high artificer": "Natural Bracket 4/5 artifact mana + infinite outlet commander.",
    "codie, vociferous codex": "Natural Bracket 4 turbo cascade-to-1-MV-spell combo commander.",
    "alaundo the seer": "Natural Bracket 4 untap storm chain commander.",
    "meria, scholar of antiquity": "Natural Bracket 4 artifact-stax parity breaker (taps Winter Orb and 0-MV artifacts for mana and impulse draw).",
    "glarb, calamity's augur": "High Bracket 3 / Bracket 4–5 top-deck commander (casts MV>=4 alternate-cost spells like Force of Will / Gush and Doomsday piles from top of library).",
    "krenko, mob boss": "Natural high-ceiling exponential token/untap combo commander.",
    "zada, hedron grinder": "Natural Bracket 4 cantrip-copy storm commander.",
    "kefka, court mage": "Natural Bracket 4 ETB/blink value & combo commander.",
}

# Curated 2-card combos fallback (with early=True for compact low-MV two-card wins).
CURATED_TWO_CARD_COMBOS: tuple[tuple[str, str, bool], ...] = (
    ("Thassa's Oracle", "Demonic Consultation", True),
    ("Thassa's Oracle", "Tainted Pact", True),
    ("Dramatic Reversal", "Isochron Scepter", True),
    ("Dockside Extortionist", "Temur Sabertooth", True),
    ("Dockside Extortionist", "Cloudstone Curio", True),
    ("Exquisite Blood", "Sanguine Bond", False),
    ("Kiki-Jiki, Mirror Breaker", "Pestermite", True),
    ("Kiki-Jiki, Mirror Breaker", "Deceiver Exarch", True),
    ("Kiki-Jiki, Mirror Breaker", "Zealous Conscripts", True),
    ("Splinter Twin", "Pestermite", True),
    ("Splinter Twin", "Deceiver Exarch", True),
    ("Mikaeus, the Unhallowed", "Triskelion", False),
    ("Mikaeus, the Unhallowed", "Walking Ballista", True),
    ("Devoted Druid", "Vizier of Remedies", True),
    ("Freed from the Real", "Selvala, Heart of the Wilds", True),
    ("Food Chain", "Eternal Scourge", True),
    ("Food Chain", "Misthollow Griffin", True),
    ("Auriok Salvagers", "Lion's Eye Diamond", True),
    ("Helm of Obedience", "Leyline of the Void", True),
    ("Painter's Servant", "Grindstone", True),
    ("Pili-Pala", "Grand Architect", True),
    ("Basalt Monolith", "Rings of Brighthearth", True),
    ("Grim Monolith", "Power Artifact", True),
    ("Worldgorger Dragon", "Animate Dead", True),
    ("Worldgorger Dragon", "Dance of the Dead", True),
    ("Curiosity", "Niv-Mizzet, the Firemind", False),
    ("Curiosity", "Niv-Mizzet, Parun", False),
    ("Helm of the Host", "Godo, Bandit Warlord", False),
    ("Heliod, Sun-Crowned", "Walking Ballista", False),
    ("Heliod, Sun-Crowned", "Spike Feeder", True),
    ("Vito, Thorn of the Dusk Rose", "Exquisite Blood", False),
    ("Bloodthirsty Conqueror", "Sanguine Bond", False),
    ("Bloodthirsty Conqueror", "Vito, Thorn of the Dusk Rose", False),
    ("Cephalid Illusionist", "Nomads en-Kor", True),
    ("Spike Feeder", "Archangel of Thune", False),
    ("Midnight Guard", "Presence of Gond", False),
    ("Demonic Consultation", "Jace, Wielder of Mysteries", True),
    ("Tainted Pact", "Laboratory Maniac", True),
    ("Demonic Consultation", "Laboratory Maniac", True),
    ("Dualcaster Mage", "Twinflame", False),
    ("Dualcaster Mage", "Heat Shimmer", False),
    ("Dualcaster Mage", "Molten Duplication", False),
    ("Village Bell-Ringer", "Kiki-Jiki, Mirror Breaker", True),
    ("Restoration Angel", "Kiki-Jiki, Mirror Breaker", True),
    ("Felidar Guardian", "Kiki-Jiki, Mirror Breaker", True),
    ("Phyrexian Altar", "Gravecrawler", True),
    ("Time Sieve", "Thopter Assembly", False),
    ("Chatterfang, Squirrel General", "Pitiless Plunderer", True),
    ("Kinnan, Bonder Prodigy", "Basalt Monolith", True),
    ("Leonin Relic-Warder", "Animate Dead", True),
    ("Leonin Relic-Warder", "Dance of the Dead", True),
    ("Leonin Relic-Warder", "Necromancy", True),
    ("Abdel Adrian, Gorion's Ward", "Animate Dead", True),
    ("Abdel Adrian, Gorion's Ward", "Dance of the Dead", True),
    ("Abdel Adrian, Gorion's Ward", "Necromancy", True),
)

# Community EDHREC salt scores for the most-flagged Commander staples (0-4 scale).
SALT_SCORES: dict[str, float] = {
    "stasis": 3.5, "winter orb": 3.4, "armageddon": 3.3, "tergrid, god of fright": 3.2,
    "vorinclex, voice of hunger": 3.1, "static orb": 3.1, "ravages of war": 3.1, "sunder": 3.0,
    "expropriate": 2.9, "jin-gitaxias, core augur": 2.9, "jokulhaups": 2.9, "obliterate": 2.9,
    "grand arbiter augustin iv": 2.8, "drannith magistrate": 2.8, "humility": 2.8, "back to basics": 2.8,
    "blood moon": 2.7, "rhystic study": 2.6, "cyclonic rift": 2.6, "smothering tithe": 2.5,
    "thassa's oracle": 2.6, "opposition agent": 2.6, "narset, parter of veils": 2.6, "farewell": 2.5,
    "fierce guardianship": 2.4, "force of will": 2.4, "the one ring": 2.4, "orcish bowmasters": 2.4,
    "consecrated sphinx": 2.3, "dockside extortionist": 2.3, "mana drain": 2.2, "teferi's protection": 2.2,
    "ad nauseam": 2.2, "underworld breach": 2.2, "demonic tutor": 2.1, "vampiric tutor": 2.1,
    "imperial seal": 2.1, "mana vault": 2.1, "ancient tomb": 2.1, "gaea's cradle": 2.3,
    "the tabernacle at pendrell vale": 3.0, "glacial chasm": 2.5, "seedborn muse": 2.1,
    "time stretch": 2.5, "time warp": 2.2, "nexus of fate": 2.4, "torabran": 1.8, "bolas's citadel": 2.1,
    "necropotence": 2.1, "aura shards": 2.2, "dictate of erebos": 2.2, "grave pact": 2.2,
}

# 10 Enabler x Payoff synergy axes (EDHcheck /how-we-score).
_SYNERGY_AXES: dict[str, tuple[re.Pattern[str], re.Pattern[str]]] = {
    "blink": (
        re.compile(r"exile (?:up to \w+ )?(?:another )?target [^.]*then return|flicker|conjurer's closet|teleportation circle"),
        re.compile(r"\bwhen (?:this |~ |it |\w+ )?enters\b"),
    ),
    "graveyard": (
        re.compile(r"\bmill\b|put the top [^.]*into your graveyard|\bsurveil\b|\bdiscard\b|\bentomb\b|\bdredge\b"),
        re.compile(r"from your graveyard|\bflashback\b|\bescape\b|\bdelve\b|\bthreshold\b|\bdelirium\b|\bretrace\b|\bunearthed?\b"),
    ),
    "sacrifice": (
        re.compile(r"\bsacrifice (?:a|an|another|one or more) (?:creature|artifact|permanent|token)"),
        re.compile(r"whenever (?:this creature or )?(?:a|another|one or more) [^.]*(?:dies|you sacrifice|leaves? your graveyard)|\bwhen this creature dies\b"),
    ),
    "tokens": (
        re.compile(r"\bcreates? (?:a|an|one|two|three|four|x|\d+|that many) [^.]*tokens?\b|\bamass\b|\bfabricate\b"),
        re.compile(r"\btokens? you control\b|for each (?:creature|token) you control|\bpopulate\b|twice that many of those tokens|convoke"),
    ),
    "counters": (
        re.compile(r"put (?:a|an|one|two|x|\d+|that many) (?:\+1/\+1|-1/-1) counters?|\bproliferate\b|\bundying\b|\bpersist\b|\bfabricate\b|additional \+1/\+1 counter"),
        re.compile(r"(?:\+1/\+1|-1/-1) counters?|remove (?:a|all|any number of) counters?|\bundying\b|\bpersist\b"),
    ),
    "spellslinger": (
        re.compile(r"\binstant\b|\bsorcery\b"),
        re.compile(r"whenever you cast (?:an|a) (?:instant|sorcery|noncreature)|\bmagecraft\b|\bstorm\b|\bprowess\b"),
    ),
    "artifacts": (
        re.compile(r"\bartifact\b|treasure token|clue token|food token|blood token"),
        re.compile(r"artifacts? you control|\baffinity for artifacts\b|\bmetalcraft\b|\bimprovise\b|whenever an artifact"),
    ),
    "lifegain": (
        re.compile(r"\bgains? (?:\d+|x|that much) life\b|\blifelink\b"),
        re.compile(r"whenever you gain life|if you gained (?:\d+ or more )?life"),
    ),
    "landfall": (
        re.compile(r"search your library for [^.]*land|play an additional land"),
        re.compile(r"whenever a land (?:you control )?enters|\blandfall\b"),
    ),
    "reanimator": (
        re.compile(r"\bmill\b|\bdiscard\b|search your library for a card, put that card into your graveyard"),
        re.compile(r"return target creature card from (?:a|your) graveyard to the battlefield|put .*creature cards? from .*graveyard.* onto the battlefield"),
    ),
    "upkeep": (
        re.compile(r"additional upkeep|can't be blocked|\bhaste\b|\bdouble strike\b|you become the monarch|take the initiative"),
        re.compile(r"at the beginning of (?:your|each|enchanted player's) (?:first )?upkeep|you become the monarch|take the initiative|\bsuspend\b|time counter"),
    ),
}
def _is_game_changer(card: dict[str, Any], fallback_name: str = "") -> bool:
    flag = card.get("game_changer")
    if flag is not None:
        return bool(flag)
    return _front_lower(card.get("name") or fallback_name) in GAME_CHANGERS_SET


def _is_fast_mana(card: dict[str, Any]) -> bool:
    name = _front_lower(card.get("name") or "")
    if name in FAST_MANA_SET:
        return True
    tl = front_type_line(card)
    if "Land" in tl or "Creature" in tl:
        return False
    cmc = float(card.get("cmc") or 0)
    if cmc > 1:
        return False
    text = re.sub(r"\([^)]*\)", "", oracle_text(card).lower())
    return bool(re.search(r"add \{[wubrgc]\}\{[wubrgc]\}|add (?:two|three|four|five) mana", text))


def _is_extra_turn(card: dict[str, Any]) -> bool:
    name = _front_lower(card.get("name") or "")
    if name in EXTRA_TURN_SET:
        return True
    text = re.sub(r"\([^)]*\)", "", oracle_text(card).lower())
    return bool(re.search(r"takes? an extra turn after this one", text)) and "you lose the game" not in text


def _is_mld(card: dict[str, Any]) -> bool:
    name = _front_lower(card.get("name") or "")
    if name in MLD_SET:
        return True
    text = re.sub(r"\([^)]*\)", "", oracle_text(card).lower())
    return bool(re.search(r"\b(?:destroy|exile|sacrifice) all lands\b|nonbasic lands are mountains", text))


def _is_instant_speed(card: dict[str, Any]) -> bool:
    tl = front_type_line(card)
    if "Instant" in tl:
        return True
    keywords = [k.lower() for k in (card.get("keywords") or [])]
    if "flash" in keywords:
        return True
    text = re.sub(r"\([^)]*\)", "", oracle_text(card).lower())
    return bool(re.search(r"\bflash\b|as though (?:it|they) had flash", text))


def _is_free_spell(card: dict[str, Any]) -> bool:
    name = _front_lower(card.get("name") or "")
    if name in FREE_SPELL_SET:
        return True
    if not _is_instant_speed(card):
        return False
    text = re.sub(r"\([^)]*\)", "", oracle_text(card).lower())
    return "rather than pay this spell's mana cost" in text or "without paying its mana cost" in text


def _synergy_profile(nonland_cards: list[dict[str, Any]]) -> dict[str, Any]:
    card_features = [
        (
            f"{front_type_line(c)} {re.sub(r'\([^)]*\)', '', oracle_text(c))}".lower(),
            set((c.get("forge_tags") or {}).get("synergy_enables") or ()),
            set((c.get("forge_tags") or {}).get("synergy_needs") or ()),
        )
        for c in nonland_cards
    ]
    axes: dict[str, dict[str, int]] = {}
    for axis, (enabler_pat, payoff_pat) in _SYNERGY_AXES.items():
        enablers = 0
        payoffs = 0
        for text, f_enables, f_needs in card_features:
            if enabler_pat.search(text) or axis in f_enables:
                enablers += 1
            if payoff_pat.search(text) or axis in f_needs:
                payoffs += 1
        score = min(enablers, payoffs)
        if enablers or payoffs:
            axes[axis] = {"enablers": enablers, "payoffs": payoffs, "score": score}
    signature = [
        {"axis": k, **v}
        for k, v in sorted(axes.items(), key=lambda kv: (-kv[1]["score"], -kv[1]["payoffs"], kv[0]))
        if v["score"] >= 3
    ]
    total_axis = sum(v["score"] for v in axes.values())
    synergy_score = round(min(10.0, total_axis * 0.45), 1)
    return {
        "score": synergy_score,
        "bonus": round(min(0.8, synergy_score * 0.08), 2),
        "signature_axes": signature,
        "axes": axes,
    }


def _detect_combos_and_tiers(
    deck_names_lower: set[str],
    spellbook_combos: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    two_card: list[dict[str, Any]] = []
    three_plus: list[dict[str, Any]] = []
    template_combos: list[dict[str, Any]] = []
    seen_pairs: set[tuple[str, ...]] = set()

    for c in spellbook_combos or []:
        pieces = [p for p in (c.get("cards") or []) if p]
        if not pieces:
            continue
        also_req = c.get("also_requires") or []
        key = tuple(sorted(_front_lower(p) for p in pieces)) + tuple(also_req)
        if key in seen_pairs:
            continue
        seen_pairs.add(key)
        tag = str(c.get("bracket_tag") or "").upper()
        # Commander Spellbook BracketTagEnum: 'R' (Ruthless), 'P' (Powerful) = early/Bracket 4+;
        # 'S' (Spicy) = late/Bracket 3; 'C' (Core), 'O' (Oddball), 'E' (Exhibition) = Bracket 1-2 (needs payoff).
        is_early = tag in {"R", "P", "4", "5", "EARLY", "RUTHLESS", "POWERFUL"} or (not tag and len(pieces) == 2)
        is_non_winning_two_card = len(pieces) <= 2 and tag in {"E", "O", "C", "1", "2"}
        item = {"cards": pieces, "early": is_early, "produces": c.get("produces"), "also_requires": also_req or None}
        # EDHcheck rule (05~mod.szojk4.js): `e.cards.length <= 2 && !e.requires?.length`
        # Combos with template `also_requires` ("+ needs Creature with Persist or Undying") are 3-card / template loops, not 2-card combos.
        if also_req:
            template_combos.append(item)
        elif len(pieces) <= 2 and not is_non_winning_two_card:
            two_card.append(item)
        else:
            three_plus.append(item)

    for a, b, is_early in CURATED_TWO_CARD_COMBOS:
        ka, kb = _front_lower(a), _front_lower(b)
        if ka in deck_names_lower and kb in deck_names_lower:
            key = tuple(sorted((ka, kb)))
            if key not in seen_pairs:
                seen_pairs.add(key)
                two_card.append({"cards": [a, b], "early": is_early})

    return {
        "two_card_combos": two_card,
        "three_plus_combos": three_plus,
        "template_combos": template_combos,
        "early_two_card": any(c["early"] for c in two_card),
        "late_two_card": any(not c["early"] for c in two_card),
        "total_combos": len(two_card) + len(three_plus),
        "total_including_templates": len(two_card) + len(three_plus) + len(template_combos),
    }


BRACKET_LABELS = {1: "Exhibition", 2: "Core", 3: "Upgraded", 4: "Optimized", 5: "cEDH"}


def _instant_interaction_ratio(
    resolved: list[tuple[Any, dict[str, Any]]],
    roles: dict[str, list[str]],
) -> float:
    interaction_names = set(roles.get("removal", [])) | set(roles.get("counterspell", [])) | set(roles.get("board_wipe", []))
    if not interaction_names:
        return 0.0
    instant_interaction = sum(
        1 for _, c in resolved if c.get("name") in interaction_names and _is_instant_speed(c)
    )
    return round(instant_interaction / max(1, len(interaction_names)), 2)


def _power_tier(power_total: float) -> str:
    if power_total >= 9.5:
        return "Bleeding Edge"
    if power_total >= 9.0:
        return "Razor's Edge"
    if power_total >= 8.5:
        return "Hyper-Tuned"
    if power_total >= 8.0:
        return "Elite"
    if power_total >= 7.0:
        return "High Power"
    if power_total >= 5.5:
        return "Tuned"
    if power_total >= 4.0:
        return "Focused"
    return "Casual"


def _compute_power_scores(
    *,
    resolved: list[tuple[Any, dict[str, Any]]],
    nonland_count: int,
    avg_cmc: float,
    roles: dict[str, list[str]],
    interaction_total: int,
    instant_ratio: float,
    game_changers: list[str],
    combo_info: dict[str, Any],
    synergy: dict[str, Any],
) -> tuple[float, dict[str, Any]]:
    tutors_count = len(set(roles.get("tutor", [])))
    ramp_count = len(set(roles.get("ramp", [])))
    draw_count = len(set(roles.get("card_draw", [])))
    protection_count = len(set(roles.get("protection", [])))
    recursion_count = len(set(roles.get("recursion", [])))

    ramp_pct = ramp_count / nonland_count
    draw_pct = draw_count / nonland_count
    removal_pct = interaction_total / nonland_count

    # Salt average over salty cards present (or 0.15 baseline)
    salty_hits = [
        SALT_SCORES[_front_lower(c.get("name", e.name))]
        for e, c in resolved
        if _front_lower(c.get("name", e.name)) in SALT_SCORES
    ]
    avg_salt = sum(salty_hits) / max(4, len(salty_hits)) if salty_hits else 0.15

    # 8 EDHcheck 0-10 sub-scores (exact EDHcheck weights and scalers)
    tutor_sub = min(10.0, tutors_count * 0.9)
    combo_sub = min(10.0, combo_info["total_combos"] * 3.2)
    gc_sub = min(10.0, len(game_changers) * 2.0)
    curve_sub = max(0.0, min(10.0, (4.2 - avg_cmc) * 3.8))
    draw_sub = min(10.0, draw_pct * 65.0)
    ramp_sub = min(10.0, ramp_pct * 70.0)
    salt_sub = min(10.0, avg_salt * 4.0)
    removal_sub = min(10.0, removal_pct * 47.0)

    interaction_score = round(min(10.0, removal_sub * (0.65 + 0.35 * instant_ratio)), 1)
    interaction_bonus = round(min(0.4, interaction_score * 0.04), 2)
    engine_momentum_bonus = (
        round(min(0.95, synergy["score"] * 0.095), 2)
        if nonland_count >= 50 and combo_info["total_combos"] < 2 and synergy["score"] >= 8.0 and draw_count >= 10 and interaction_total >= 10
        else 0.0
    )

    weighted = (
        tutor_sub * 0.18
        + combo_sub * 0.15
        + gc_sub * 0.15
        + curve_sub * 0.12
        + draw_sub * 0.12
        + ramp_sub * 0.10
        + salt_sub * 0.10
        + removal_sub * 0.08
    )
    raw = weighted + synergy["bonus"] + interaction_bonus + engine_momentum_bonus

    missing_levers: list[str] = []
    if tutors_count < 6:
        missing_levers.append(
            f"Tutors (18% weight): {tutors_count} in deck ({round(tutor_sub * 0.18, 2)}/1.80 raw pts; add 6+ budget tutors/transmutes for +0.97 to +1.80 pts)."
        )
    if combo_info["total_combos"] < 2:
        tmpl_note = (
            f" ({len(combo_info['template_combos'])} template combo(s) have `also_requires` and score 0 on EDHcheck)"
            if combo_info["template_combos"]
            else ""
        )
        missing_levers.append(
            f"Combos (15% weight): {combo_info['total_combos']} explicit combo(s){tmpl_note} ({round(combo_sub * 0.15, 2)}/1.50 raw pts; add 2-3 explicit Spellbook combos for +0.96 to +1.50 pts)."
        )
    if len(game_changers) < 2:
        missing_levers.append(
            f"Game Changers (15% weight): {len(game_changers)} in deck ({round(gc_sub * 0.15, 2)}/1.50 raw pts; add 2-3 budget Game Changers for +0.60 to +0.90 pts in Bracket 3)."
        )

    speed_score = round(min(10.0, curve_sub * 0.35 + ramp_sub * 0.25 + tutor_sub * 0.20 + combo_sub * 0.20), 1)
    consistency_score = round(min(10.0, (draw_sub * 0.45 + tutor_sub * 0.35 + ramp_sub * 0.20) * 0.83), 1)
    token_axis = (synergy["axes"].get("tokens") or {}).get("score", 0)
    resilience_score = round(min(10.0, (protection_count + recursion_count) * 0.35 + token_axis * 0.2), 1)

    power_report: dict[str, Any] = {
        "total": 0.0,
        "tier": "",
        "raw_weighted": round(weighted, 2),
        "speed": speed_score,
        "consistency": consistency_score,
        "saltiness": round(salt_sub, 1),
        "interaction": interaction_score,
        "synergy": synergy["score"],
        "resilience": resilience_score,
        "missing_levers": missing_levers,
        "components": {
            "tutors": round(tutor_sub, 1),
            "combos": round(combo_sub, 1),
            "game_changers": round(gc_sub, 1),
            "mana_curve": round(curve_sub, 1),
            "card_draw": round(draw_sub, 1),
            "ramp": round(ramp_sub, 1),
            "salt": round(salt_sub, 1),
            "removal": round(removal_sub, 1),
            "synergy_bonus": synergy["bonus"],
            "interaction_bonus": interaction_bonus,
            "engine_momentum_bonus": engine_momentum_bonus,
            "instant_interaction_ratio": instant_ratio,
        },
    }
    return raw, power_report


def _estimate_win_turn(
    speed_score: float,
    combo_info: dict[str, Any],
    fast_mana_count: int,
    fast_tutors_count: int,
) -> str:
    if combo_info["early_two_card"] and (fast_mana_count >= 3 or fast_tutors_count >= 4 or speed_score >= 8.2):
        return "Turn 3–4"
    if combo_info["early_two_card"] or speed_score >= 6.8:
        return "Turn 5–6"
    if combo_info["total_combos"] >= 1 or speed_score >= 4.8:
        return "Turn 7–8"
    if speed_score >= 2.8:
        return "Turn 9–10"
    return "Turn 11+"


def _bracket_path(
    bracket: int,
    game_changers: list[str],
    combo_info: dict[str, Any],
    mld: list[str],
    extra_turns: list[str],
    fast_mana: list[str] = (),
) -> list[str]:
    path: list[str] = []
    if bracket >= 4:
        if len(game_changers) > 3:
            excess = len(game_changers) - 3
            path.append(f"Cut {excess} Game Changer(s) (from {', '.join(game_changers)}) to fit Bracket 3's 3-card limit.")
        if combo_info["early_two_card"]:
            early_names = [" + ".join(c["cards"]) for c in combo_info["two_card_combos"] if c["early"]]
            path.append(f"Break up early 2-card infinite combo(s) ({'; '.join(early_names[:2])}) to drop to Bracket 3.")
        if mld:
            path.append(f"Cut mass land denial ({', '.join(mld)}) to play in Brackets 1–3.")
        if len(extra_turns) >= 3:
            path.append(f"Trim extra-turn spells ({', '.join(extra_turns)}) to at most 2 (no chaining extra turns in Bracket 3).")
    if bracket == 3:
        if game_changers:
            path.append(f"Cut all {len(game_changers)} Game Changer(s) ({', '.join(game_changers)}) to drop to Bracket 2.")
        if combo_info["late_two_card"]:
            late_names = [" + ".join(c["cards"]) for c in combo_info["two_card_combos"] if not c["early"]]
            path.append(f"Remove 2-card combo(s) ({'; '.join(late_names[:2])}) to drop to Bracket 2.")
        if len(extra_turns) > 1:
            path.append(f"Trim extra-turn spells ({', '.join(extra_turns)}) down to at most 1 for Bracket 2.")
    if bracket == 2:
        if extra_turns:
            path.append(f"Cut extra-turn spell(s) ({', '.join(extra_turns)}) to drop to Bracket 1.")
        if fast_mana:
            path.append(f"Cut fast mana ({', '.join(fast_mana)}) to drop to Bracket 1.")
        if combo_info["three_plus_combos"]:
            path.append("Remove 3+ card infinite combo(s) to drop to Bracket 1.")
    return path


def _tune_up_path(
    bracket: int,
    avg_cmc: float,
    game_changers: list[str],
    combo_info: dict[str, Any],
    one_mana_ramp: list[str],
    fast_tutors: list[str],
    free_spells: list[str],
) -> list[str]:
    steps: list[str] = []
    if bracket <= 2:
        if avg_cmc > 2.6:
            steps.append(f"Speed: lower average nonland MV from {avg_cmc:.2f} toward <= 2.60 by replacing 4+ MV pet cards with 1–2 MV synergy.")
        if len(one_mana_ramp) < 5:
            steps.append(f"Acceleration: add 1-mana ramp (currently {len(one_mana_ramp)}; target 5+) to cast the commander a turn earlier.")
        if not game_changers:
            steps.append("High-impact slots: add up to 3 on-plan Game Changers or a Turn 7+ combo finisher for Bracket 3.")
    elif bracket == 3:
        if avg_cmc > 2.2:
            steps.append(f"Efficiency: lower average nonland MV from {avg_cmc:.2f} toward <= 2.20 for Turn 5–6 Bracket 4 pace.")
        if combo_info["total_combos"] < 2 or len(fast_tutors) < 4:
            steps.append(
                f"Consistency: add overlapping 2-card combos (currently {combo_info['total_combos']}) and <=2 MV tutors (currently {len(fast_tutors)}; target 4+)."
            )
        if len(free_spells) < 2:
            steps.append(f"Disruption: add free/1-mana instant interaction (currently {len(free_spells)} free spells) to protect wins and stop Turn 4–5 threats.")
    elif bracket == 4:
        steps.append("cEDH (Bracket 5): align with tournament metagame fast mana (3+ Mox/Vault/Tomb), 5+ 1-2 MV tutors, and free stack interaction.")
    return steps


def _decide_bracket(
    *,
    raw: float,
    avg_cmc: float,
    speed_score: float,
    game_changers: list[str],
    fast_mana: list[str],
    extra_turns: list[str],
    mld: list[str],
    combo_info: dict[str, Any],
    tutors_count: int,
    fast_tutors: list[str] = (),
    one_mana_ramp: list[str] = (),
    free_spells: list[str] = (),
    commanders: list[str] = (),
) -> tuple[dict[str, Any], float]:
    # Base Bracket 1..4 decision (EDHcheck decideBracket + Oct 2025 WotC update)
    b4_reasons: list[str] = []
    if len(game_changers) > 3:
        b4_reasons.append(f"{len(game_changers)} Game Changers (Bracket 3 allows up to 3)")
    if combo_info["early_two_card"]:
        b4_reasons.append("an early two-card infinite combo")
    if mld:
        b4_reasons.append(f"mass land denial ({', '.join(mld[:3])})")
    if len(extra_turns) >= 3:
        b4_reasons.append(f"{len(extra_turns)} extra-turn spells (chaining extra turns is Bracket 4+)")

    b3_reasons: list[str] = []
    if 1 <= len(game_changers) <= 3:
        b3_reasons.append(f"{len(game_changers)} Game Changer(s) ({', '.join(game_changers)})")
    if combo_info["late_two_card"]:
        b3_reasons.append("a late two-card infinite combo")
    if len(extra_turns) == 2:
        b3_reasons.append(f"2 extra-turn spells ({', '.join(extra_turns)})")

    b2_reasons: list[str] = []
    if len(extra_turns) == 1:
        b2_reasons.append(f"1 extra-turn spell ({extra_turns[0]})")
    if fast_mana:
        b2_reasons.append(f"{len(fast_mana)} fast mana source(s) (e.g. {fast_mana[0]})")
    if combo_info["three_plus_combos"]:
        b2_reasons.append(f"{len(combo_info['three_plus_combos'])} infinite combo(s) of 3+ cards")

    if b4_reasons:
        base_bracket = 4
    elif b3_reasons:
        base_bracket = 3
    elif b2_reasons or raw >= 6.5:
        base_bracket = 2
        if raw >= 6.5 and not b2_reasons:
            b2_reasons.append("a power score of 6.5+")
    else:
        base_bracket = 1

    # Soft floor/cap before top-end stretch
    adjusted = raw
    if base_bracket == 4 and adjusted < 6.8:
        adjusted = 6.8
    elif base_bracket == 1 and adjusted > 4.2:
        adjusted = 4.2

    stretched = 6.0 + (adjusted - 6.0) * 1.3 if adjusted > 6.0 else adjusted
    power_total = round(min(10.0, max(0.0, stretched)), 1)

    # Check Bracket 5 cEDH upgrade signals
    cedh_signals: list[str] = []
    if len(game_changers) >= 5:
        cedh_signals.append(f"{len(game_changers)} Game Changers")
    if len(fast_mana) >= 3:
        cedh_signals.append(f"{len(fast_mana)} fast mana")
    if combo_info["early_two_card"]:
        cedh_signals.append("an early two-card combo")
    if tutors_count >= 5:
        cedh_signals.append(f"{tutors_count} tutors")
    if len(free_spells) >= 2:
        cedh_signals.append(f"{len(free_spells)} free interaction spells")
    if power_total >= 8.5:
        cedh_signals.append(f"power {power_total:.1f}")

    bracket = base_bracket
    if (
        base_bracket == 4
        and len(game_changers) >= 4
        and (combo_info["early_two_card"] or power_total >= 8.5)
        and len(cedh_signals) >= 3
    ):
        bracket = 5
        if power_total < 8.6:
            power_total = 8.6
        reason = f"cEDH profile: {', '.join(cedh_signals)}."
    elif base_bracket == 4:
        reason = f"Optimized: {', '.join(b4_reasons)}."
    elif base_bracket == 3:
        reason = f"Upgraded: {', '.join(b3_reasons)}."
    elif base_bracket == 2:
        reason = f"Core: {', '.join(b2_reasons)}."
    else:
        reason = "Exhibition: no Game Changers, fast mana, extra turns, mass land denial, or infinite combos."

    estimated_win_turn = _estimate_win_turn(speed_score, combo_info, len(fast_mana), len(fast_tutors))

    bracket_up_warning = None
    if bracket == 2 and (power_total >= 6.5 or estimated_win_turn in {"Turn 5–6", "Turn 7–8"}):
        bracket_up_warning = (
            f"Bracket 2 by card restrictions, but its {power_total:.1f} power score and {estimated_win_turn} clock "
            "play like Bracket 3 (WotC expects 8+ turns in Bracket 2). Bracket up at the table."
        )
    elif bracket == 3 and (power_total >= 7.5 or estimated_win_turn == "Turn 5–6"):
        bracket_up_warning = (
            f"Bracket 3 by card restrictions, but its {power_total:.1f} power score and {estimated_win_turn} clock "
            "play like Bracket 4 (WotC expects 6+ turns before a win in Bracket 3). Mention its speed or play at Bracket 4."
        )

    commander_fit = next(
        (NATURAL_B4_COMMANDERS[_front_lower(cmd)] for cmd in commanders if _front_lower(cmd) in NATURAL_B4_COMMANDERS),
        None,
    )

    bracket_report = {
        "bracket": bracket,
        "label": BRACKET_LABELS[bracket],
        "expected_turns": BRACKET_EXPECTED_TURNS[bracket],
        "estimated_win_turn": estimated_win_turn,
        "commander_bracket_fit": commander_fit,
        "reason": reason,
        "bracket_up_warning": bracket_up_warning,
        "bracket_path": _bracket_path(bracket, game_changers, combo_info, mld, extra_turns, fast_mana),
        "tune_up": _tune_up_path(
            bracket, avg_cmc, game_changers, combo_info, list(one_mana_ramp), list(fast_tutors), list(free_spells)
        ),
        "flags": {
            "game_changers": game_changers,
            "fast_mana": fast_mana,
            "one_mana_ramp": list(one_mana_ramp),
            "fast_tutors": list(fast_tutors),
            "free_spells": list(free_spells),
            "extra_turns": extra_turns,
            "mass_land_denial": mld,
            "two_card_combos": combo_info["two_card_combos"],
            "three_plus_combos": len(combo_info["three_plus_combos"]),
            "early_two_card_combo": combo_info["early_two_card"],
            "late_two_card_combo": combo_info["late_two_card"],
        },
    }
    return bracket_report, power_total


def _school_score(
    *,
    nonland_cards: list[dict[str, Any]],
    lands: int,
    avg_cmc: float,
    roles: dict[str, list[str]],
    interaction_total: int,
    instant_ratio: float,
    combo_info: dict[str, Any],
) -> dict[str, Any]:
    nonland_count = max(1, len(nonland_cards))
    tutors_count = len(set(roles.get("tutor", [])))
    ramp_count = len(set(roles.get("ramp", [])))
    draw_count = len(set(roles.get("card_draw", [])))
    draw_on_cast = len(set(roles.get("draw_on_cast", [])))
    immediate_draw_share = draw_on_cast / max(1, draw_count) if draw_count else 0.0
    veggie_total = ramp_count + draw_count + interaction_total + tutors_count
    nero_score = round(
        min(
            10.0,
            min(4.0, max(0.0, (3.4 - avg_cmc) * 3.1))
            + min(3.5, veggie_total / 9.5)
            + min(2.5, immediate_draw_share * 1.5 + min(1.0, combo_info["total_combos"] * 0.25)),
        ),
        1,
    )
    instant_nonlands = sum(1 for c in nonland_cards if _is_instant_speed(c))
    defcat_score = round(min(10.0, instant_ratio * 6.0 + min(4.0, (instant_nonlands / nonland_count) * 12.0)), 1)

    # Based 33-card core alignment: how well role counts scale into 3 x 33 games
    per_33 = {
        "lands": round(lands / 3.0, 1),
        "ramp": round(ramp_count / 3.0, 1),
        "card_draw": round(draw_count / 3.0, 1),
        "interaction": round(interaction_total / 3.0, 1),
    }
    uneven_roles = [
        name for name, count in (("lands", lands), ("ramp", ramp_count), ("card_draw", draw_count), ("interaction", interaction_total))
        if count % 3 != 0
    ]
    combo_piece_counts: Counter[str] = Counter()
    for c in combo_info["two_card_combos"] + combo_info["three_plus_combos"] + combo_info["template_combos"]:
        for piece in c.get("cards") or []:
            combo_piece_counts[piece] += 1
    keystone_cards = [card for card, cnt in combo_piece_counts.most_common() if cnt >= 3]

    based_hits = (
        (3.0 if 9.5 <= per_33["lands"] <= 13.5 else 1.0)
        + (2.5 if per_33["ramp"] >= 2.5 else per_33["ramp"])
        + (2.5 if per_33["card_draw"] >= 3.0 else per_33["card_draw"] * 0.8)
        + (2.0 if per_33["interaction"] >= 3.0 else per_33["interaction"] * 0.6)
        - 0.3 * len(uneven_roles)
    )
    based_score = round(max(0.0, min(10.0, based_hits)), 1)

    draw_set = set(roles.get("card_draw", []))
    tutor_set = set(roles.get("tutor", []))
    conditional_sac_draw = sorted({
        c.get("name", "")
        for c in nonland_cards
        if c.get("name", "") in draw_set
        and re.search(
            r"additional cost to cast this spell, sacrifice|sacrifice (?:a|another) (?:creature|artifact|permanent)[^.]*:|\bwhenever (?:a|another) (?:nontoken )?creature you control dies\b",
            re.sub(r"\([^)]*\)", "", oracle_text(c).lower()),
        )
    })
    slow_hand_tutors = sorted({
        c.get("name", "")
        for c in nonland_cards
        if (
            c.get("name", "") in tutor_set
            and float(c.get("cmc") or 0) >= 3
            and not re.search(
                r"onto the battlefield|into your graveyard",
                re.sub(r"\([^)]*\)", "", oracle_text(c).lower()),
            )
        )
        or _front_lower(c.get("name", "")) == "case of the stashed skeleton"
    })
    situational_top_end = sorted({
        c.get("name", "")
        for c in nonland_cards
        if float(c.get("cmc") or 0) >= 6
        and not re.search(
            r"\b(?:delve|convoke|affinity|improvise|undying|persist|cycling)\b|rather than pay|costs? \{.\} less",
            re.sub(r"\([^)]*\)", "", oracle_text(c).lower()),
        )
    })

    school_notes: list[str] = []
    if avg_cmc > 2.5:
        school_notes.append(f"NeRo: average nonland MV is {avg_cmc} (target <= 2.2 for fast Bracket 4).")
    if draw_count and immediate_draw_share < 0.5:
        school_notes.append(f"NeRo: only {draw_on_cast}/{draw_count} draw spells are draw_on_cast; replace slow engines with immediate draw.")
    if len(conditional_sac_draw) >= 3 and len(conditional_sac_draw) / max(1, draw_count) > 0.35:
        school_notes.append(
            f"Clunk/Whiff risk: {len(conditional_sac_draw)}/{draw_count} draw cards require sacrificing a permanent ({', '.join(conditional_sac_draw[:4])}); replace with unconditional draw so hands without fodder do not brick."
        )
    if len(slow_hand_tutors) >= 3:
        school_notes.append(
            f"Clunk/Tempo risk: {len(slow_hand_tutors)} slow 3+ MV/setup tutors ({', '.join(slow_hand_tutors[:4])}); prefer 1–2 MV or straight-to-battlefield/graveyard tutors."
        )
    if len(situational_top_end) > 5:
        school_notes.append(
            f"Clunk/Floor risk (Salubrious Snail rule): {len(situational_top_end)} cards cost 6+ MV without cost reduction ({', '.join(situational_top_end[:4])}); cap at <= 5 so opening hands stay functional."
        )
    if instant_ratio < 0.6 and interaction_total > 0:
        school_notes.append(f"Defcat: only {int(instant_ratio * 100)}% of interaction is instant-speed; prefer Instant/Flash answers.")
    if uneven_roles:
        school_notes.append(f"Based 3x33: {', '.join(uneven_roles)} are not clean multiples of 3 across Piles A/B/C.")
    if keystone_cards:
        school_notes.append(
            f"Based 3x33: keystone combo pieces in 3+ lines ({', '.join(keystone_cards[:3])}) need functional twins or tutors across Piles B/C."
        )

    return {
        "total": round((nero_score + defcat_score + based_score) / 3.0, 1),
        "nero": nero_score,
        "defcat": defcat_score,
        "based_33": based_score,
        "per_33_game": per_33,
        "uneven_3x33_roles": uneven_roles,
        "keystone_combo_pieces": keystone_cards,
        "clunk_risk": {
            "conditional_sac_draw": conditional_sac_draw,
            "slow_hand_tutors": slow_hand_tutors,
            "situational_top_end": situational_top_end,
        },
        "notes": school_notes,
    }


def _score_and_bracket(
    *,
    resolved: list[tuple[Any, dict[str, Any]]],
    nonland_cards: list[dict[str, Any]],
    lands: int,
    avg_cmc: float,
    roles: dict[str, list[str]],
    interaction_total: int,
    game_changers: list[str],
    spellbook_combos: list[dict[str, Any]] | None = None,
    commanders: list[str] = (),
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    deck_names_lower = {_front_lower(c.get("name", e.name)) for e, c in resolved}
    fast_mana = sorted({c.get("name", e.name) for e, c in resolved if _is_fast_mana(c)})
    extra_turns = sorted({c.get("name", e.name) for e, c in resolved if _is_extra_turn(c)})
    mld = sorted({c.get("name", e.name) for e, c in resolved if _is_mld(c)})
    free_spells = sorted({c.get("name", e.name) for e, c in resolved if _is_free_spell(c)})
    ramp_set = set(roles.get("ramp", []))
    tutor_set = set(roles.get("tutor", []))
    one_mana_ramp = sorted({c.get("name", e.name) for e, c in resolved if c.get("name", e.name) in ramp_set and float(c.get("cmc") or 0) <= 1})
    fast_tutors = sorted({c.get("name", e.name) for e, c in resolved if c.get("name", e.name) in tutor_set and float(c.get("cmc") or 0) <= 2})
    combo_info = _detect_combos_and_tiers(deck_names_lower, spellbook_combos)

    instant_ratio = _instant_interaction_ratio(resolved, roles)
    synergy = _synergy_profile(nonland_cards)

    raw, power_report = _compute_power_scores(
        resolved=resolved,
        nonland_count=max(1, len(nonland_cards)),
        avg_cmc=avg_cmc,
        roles=roles,
        interaction_total=interaction_total,
        instant_ratio=instant_ratio,
        game_changers=game_changers,
        combo_info=combo_info,
        synergy=synergy,
    )
    bracket_report, power_total = _decide_bracket(
        raw=raw,
        avg_cmc=avg_cmc,
        speed_score=power_report["speed"],
        game_changers=game_changers,
        fast_mana=fast_mana,
        extra_turns=extra_turns,
        mld=mld,
        combo_info=combo_info,
        tutors_count=len(tutor_set),
        fast_tutors=fast_tutors,
        one_mana_ramp=one_mana_ramp,
        free_spells=free_spells,
        commanders=list(commanders),
    )
    power_report["total"] = power_total
    power_report["tier"] = _power_tier(power_total)

    school_report = _school_score(
        nonland_cards=nonland_cards,
        lands=lands,
        avg_cmc=avg_cmc,
        roles=roles,
        interaction_total=interaction_total,
        instant_ratio=instant_ratio,
        combo_info=combo_info,
    )
    return bracket_report, power_report, synergy, school_report
