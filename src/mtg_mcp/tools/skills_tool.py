"""get_skill MCP tool."""

from __future__ import annotations

from typing import Any

from ..skills import fetch_skill, tool_description


def get_skill(name: str) -> dict[str, Any]:
    """Load one deckbuilding skill and follow the instructions it returns."""
    return fetch_skill(name)


def register(mcp) -> None:
    mcp.tool(description=tool_description())(get_skill)
