"""MCP tool registration grouped by domain (see docs/architecture.md).

Tools still live on server.py while migration proceeds. register_tools(mcp) will
attach handlers from cards.py, deck.py, etc. once those modules exist.
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP


def register_tools(mcp: FastMCP) -> None:
    """Attach tool handlers to the FastMCP instance."""
    del mcp  # placeholder until tools/*.py split lands
