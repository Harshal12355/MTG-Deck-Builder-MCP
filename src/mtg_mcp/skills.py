"""Deckbuilding skills shipped with the server.

One folder under ``deck_skills/`` is one skill. ``get_skill`` and the prompt
list both read that directory, so a hosted server sees the same files.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Skill:
    name: str
    description: str
    instructions: str


def _skill_dir() -> Path:
    return Path(__file__).resolve().parent / "deck_skills"


def parse_skill(text: str) -> Skill:
    if not text.startswith("---\n"):
        raise ValueError("skill is missing frontmatter")
    try:
        end = text.index("\n---\n", 3)
    except ValueError as exc:
        raise ValueError("skill frontmatter is not closed") from exc
    name = ""
    desc: list[str] = []
    folding = False
    for line in text[4:end].splitlines():
        if line.startswith("description:"):
            rest = line.split(":", 1)[1].strip()
            folding = rest in {">", "|", ">-", "|-", ">+", "|+"}
            if rest and not folding:
                desc.append(rest.strip("\"'"))
            continue
        if folding and line.startswith("  "):
            desc.append(line.strip())
            continue
        folding = False
        if line.startswith("name:"):
            name = line.split(":", 1)[1].strip()
    instructions = text[end + 5 :].strip()
    if not name or not desc or not instructions:
        raise ValueError(f"skill {name or '(unnamed)'} needs a name, description, and body")
    return Skill(name, " ".join(desc), instructions)


def load_skills() -> dict[str, Skill]:
    root = _skill_dir()
    found: dict[str, Skill] = {}
    if not root.is_dir():
        return found
    for path in sorted(root.glob("*/SKILL.md")):
        skill = parse_skill(path.read_text(encoding="utf-8"))
        found[skill.name] = skill
    return found


def tool_description() -> str:
    loaded = load_skills()
    if not loaded:
        return "Deckbuilding skills are not installed with this server."
    lines = "\n".join(f"- {skill.name}: {skill.description}" for skill in loaded.values())
    return "Load a deckbuilding skill and follow its instructions before recommending cards.\n" + lines


def fetch_skill(name: str) -> dict[str, str | list[str]]:
    loaded = load_skills()
    skill = loaded.get(name)
    if skill is None:
        return {"error": f"Unknown skill {name!r}.", "skills": list(loaded)}
    return {"name": skill.name, "description": skill.description, "instructions": skill.instructions}


def register_prompts(mcp) -> None:
    """MCP prompts/list + prompts/get. Clients that show a prompt picker use this."""

    def _prompt(skill: Skill):
        def run() -> str:
            return skill.instructions

        run.__name__ = skill.name.replace("-", "_")
        return run

    for skill in load_skills().values():
        mcp.prompt(name=skill.name, description=skill.description)(_prompt(skill))
