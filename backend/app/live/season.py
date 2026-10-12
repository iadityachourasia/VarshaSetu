"""Declared research-season scope for the frozen Track B live worker.

The development and test studies target June--September initializations.
Some early-October rows exist for observation-window edge handling, but they
do not establish skill for general October forecasts.
"""

from __future__ import annotations

from datetime import datetime


def jjas_scope(cycle: str) -> str:
    """Classify a YYYYMMDD 00 UTC initialization, never a verification result."""
    try:
        parsed = datetime.strptime(cycle, "%Y%m%d")
        if parsed.strftime("%Y%m%d") != cycle:
            raise ValueError
    except ValueError as error:
        raise ValueError("cycle must be a valid YYYYMMDD date") from error
    return "JJAS_RESEARCH_SCOPE" if 6 <= parsed.month <= 9 else "OUTSIDE_JJAS_RESEARCH_SCOPE"
