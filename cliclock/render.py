"""ASCII rendering for cliclock.

STUB: the real ASCII digit fonts (``block`` and ``slim``), colon blink/cycle
and date line land in the follow-up rendering task. ``render_frame(now,
settings) -> str`` is the single entry point that task must implement; the
CLI only ever calls ``render_frame``.
"""

from __future__ import annotations

from datetime import datetime

from cliclock.config import Settings


def render_placeholder(now: datetime, settings: Settings) -> str:
    """Return a one-line placeholder frame (this task's stub)."""
    return f"cliclock {now.strftime('%H:%M:%S')} (placeholder render)"


def render_frame(now: datetime, settings: Settings) -> str:
    """Return the multi-line frame for ``now`` (no trailing newline).

    Currently delegates to :func:`render_placeholder`.
    """
    return render_placeholder(now, settings)
