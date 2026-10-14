"""ASCII rendering for cliclock.

``render_frame(now, settings) -> str`` is the single entry point the CLI uses.
It is a pure function of its arguments (plus the terminal width), so tests can
call it with a fixed ``datetime``.
"""

from __future__ import annotations

import shutil
from datetime import datetime

from cliclock.config import Settings

DEFAULT_FONT = "block"
GUTTER = "  "
RESET = "\x1b[0m"
SGR_CODES = {
    "red": 31, "green": 32, "yellow": 33, "blue": 34,
    "magenta": 35, "cyan": 36, "white": 37,
}

# Separator glyph keys: ":" both dots, " " blank, "." lower dot, "'" upper dot.
# The "cycle" tick style walks this sequence (":", "·", ":", "˙" in spirit).
CYCLE_SEQUENCE = (":", ".", ":", "'")

# 3x5 pixel bitmaps shared by both fonts; each font only picks how to paint a pixel.
_BITMAPS: dict[str, tuple[str, ...]] = {
    "0": ("###", "# #", "# #", "# #", "###"),
    "1": (" # ", "## ", " # ", " # ", "###"),
    "2": ("###", "  #", "###", "#  ", "###"),
    "3": ("###", "  #", "###", "  #", "###"),
    "4": ("# #", "# #", "###", "  #", "  #"),
    "5": ("###", "#  ", "###", "  #", "###"),
    "6": ("###", "#  ", "###", "# #", "###"),
    "7": ("###", "  #", "  #", "  #", "  #"),
    "8": ("###", "# #", "###", "# #", "###"),
    "9": ("###", "# #", "###", "  #", "###"),
}


def _paint(rows: tuple[str, ...], on: str, off: str) -> tuple[str, ...]:
    return tuple("".join(on if c == "#" else off for c in row) for row in rows)


def _block_font() -> dict[str, tuple[str, ...]]:
    font = {ch: _paint(rows, "██", "  ") for ch, rows in _BITMAPS.items()}
    font[":"] = ("      ", "  ██  ", "      ", "  ██  ", "      ")
    font[" "] = ("      ",) * 5
    font["."] = ("      ", "      ", "      ", "  ██  ", "      ")
    font["'"] = ("      ", "  ██  ", "      ", "      ", "      ")
    return font


def _slim_font() -> dict[str, tuple[str, ...]]:
    font = {ch: _paint(rows, "#", " ") for ch, rows in _BITMAPS.items()}
    # Slim paints single "#" pixels; only the separators use "o" dots.
    font[":"] = ("   ", " o ", "   ", " o ", "   ")
    font[" "] = ("   ",) * 5
    font["."] = ("   ", "   ", "   ", " o ", "   ")
    font["'"] = ("   ", " o ", "   ", "   ", "   ")
    return font


# 5x7 pixel bitmaps for the "tall" font.
_TALL_BITMAPS: dict[str, tuple[str, ...]] = {
    "0": (" ### ", "#   #", "#   #", "#   #", "#   #", "#   #", " ### "),
    "1": ("  #  ", " ##  ", "  #  ", "  #  ", "  #  ", "  #  ", " ### "),
    "2": (" ### ", "#   #", "    #", "   # ", "  #  ", " #   ", "#####"),
    "3": (" ### ", "#   #", "    #", "  ## ", "    #", "#   #", " ### "),
    "4": ("   # ", "  ## ", " # # ", "#  # ", "#####", "   # ", "   # "),
    "5": ("#####", "#    ", "#### ", "    #", "    #", "#   #", " ### "),
    "6": (" ### ", "#    ", "#    ", "#### ", "#   #", "#   #", " ### "),
    "7": ("#####", "    #", "   # ", "  #  ", " #   ", " #   ", " #   "),
    "8": (" ### ", "#   #", "#   #", " ### ", "#   #", "#   #", " ### "),
    "9": (" ### ", "#   #", "#   #", " ####", "    #", "    #", " ### "),
}


def _dotted_separators(on: str, off: str, width: int, rows: int,
                       top: int, bottom: int) -> dict[str, tuple[str, ...]]:
    """Separator glyphs drawn as single dots on rows ``top``/``bottom``."""
    def make(*dot_rows: int) -> tuple[str, ...]:
        blank = off * width
        dot = off * (width // 2) + on + off * (width - width // 2 - 1)
        return tuple(dot if r in dot_rows else blank for r in range(rows))
    return {":": make(top, bottom), " ": make(), ".": make(bottom), "'": make(top)}


def _tall_font() -> dict[str, tuple[str, ...]]:
    font = {ch: _paint(rows, "█", " ") for ch, rows in _TALL_BITMAPS.items()}
    font.update(_dotted_separators("█", " ", 5, 7, 2, 4))
    return font


def _led_font() -> dict[str, tuple[str, ...]]:
    """Dot-matrix: lit pixels are ``● ``, unlit are a dim ``· ``."""
    font = {ch: _paint(rows, "● ", "· ") for ch, rows in _BITMAPS.items()}
    font[":"] = ("· · · ", "· ● · ", "· · · ", "· ● · ", "· · · ")
    font[" "] = ("· · · ",) * 5
    font["."] = ("· · · ", "· · · ", "· · · ", "· ● · ", "· · · ")
    font["'"] = ("· ● · ", "· · · ", "· · · ", "· · · ", "· · · ")
    return font


def _ghost_font() -> dict[str, tuple[str, ...]]:
    """Textured: lit pixels are ``▓▓`` over a faint ``░░`` background."""
    font = {ch: _paint(rows, "▓▓", "░░") for ch, rows in _BITMAPS.items()}
    font[":"] = ("░░░░░░", "░░▓▓░░", "░░░░░░", "░░▓▓░░", "░░░░░░")
    font[" "] = ("░░░░░░",) * 5
    font["."] = ("░░░░░░", "░░░░░░", "░░░░░░", "░░▓▓░░", "░░░░░░")
    font["'"] = ("░░░░░░", "░░▓▓░░", "░░░░░░", "░░░░░░", "░░░░░░")
    return font


def _thin_font() -> dict[str, tuple[str, ...]]:
    """Compact 3-row digits drawn with box-drawing line characters."""
    return {
        "0": ("┌─┐", "│ │", "└─┘"),
        "1": ("╶┐ ", " │ ", "╶┴╴"),
        "2": ("╶─┐", "┌─┘", "└─╴"),
        "3": ("╶─┐", " ─┤", "╶─┘"),
        "4": ("╷ ╷", "└─┤", "  ╵"),
        "5": ("┌─╴", "└─┐", "╶─┘"),
        "6": ("┌─╴", "├─┐", "└─┘"),
        "7": ("╶─┐", "  │", "  ╵"),
        "8": ("┌─┐", "├─┤", "└─┘"),
        "9": ("┌─┐", "└─┤", "╶─┘"),
        ":": (" · ", "   ", " · "),
        " ": ("   ",) * 3,
        ".": ("   ", "   ", " · "),
        "'": (" · ", "   ", "   "),
    }


FONTS: dict[str, dict[str, tuple[str, ...]]] = {
    "block": _block_font(),
    "slim": _slim_font(),
    "thin": _thin_font(),
    "led": _led_font(),
    "ghost": _ghost_font(),
    "tall": _tall_font(),
}


def available_fonts() -> tuple[str, ...]:
    """Names of the selectable digit fonts."""
    return tuple(FONTS)


def glyph_lines(style: str, char: str) -> tuple[str, ...]:
    """Rows of ``char`` in font ``style`` (unknown style -> block, unknown char -> blank)."""
    font = FONTS.get(style) or FONTS[DEFAULT_FONT]
    return font.get(char) or font[" "]


def _separator_key(now: datetime, settings: Settings) -> str:
    if settings.tick_style == "cycle":
        return CYCLE_SEQUENCE[now.second % len(CYCLE_SEQUENCE)]
    return ":" if now.second % 2 == 0 else " "


def _term_columns() -> int:
    try:
        return max(0, int(shutil.get_terminal_size().columns))
    except Exception:
        return 0


def _date_text(now: datetime, settings: Settings) -> str:
    try:
        return now.strftime(settings.date_format)
    except Exception:
        return now.strftime("%Y-%m-%d")


def _compose(now: datetime, settings: Settings) -> list[str]:
    """Frame rows for ``now``, all padded to one width, with no margin or colour."""
    style = settings.digit_style
    hour_fmt = "%I" if settings.twelve_hour else "%H"
    text = now.strftime(hour_fmt) + ":" + now.strftime("%M")
    if settings.show_seconds:
        text += ":" + now.strftime("%S")

    sep = _separator_key(now, settings)
    glyphs = [glyph_lines(style, sep if ch == ":" else ch) for ch in text]
    height = len(glyphs[0])
    lines = [GUTTER.join(g[r] for g in glyphs) for r in range(height)]

    extra: list[str] = []
    if settings.twelve_hour:
        extra.append(now.strftime("%p"))
    if settings.show_date:
        extra.append(_date_text(now, settings))

    width = max(len(line) for line in lines + extra)
    lines = [line.ljust(width) for line in lines]
    if extra:
        lines.append("")  # blank spacer between the digits and the date/AM-PM
    lines += [e.center(width) for e in extra]
    return lines


def frame_size(settings: Settings) -> tuple[int, int]:
    """``(columns, rows)`` the frame needs; constant for a given settings object."""
    lines = _compose(datetime(2000, 1, 1, 12, 0, 0), settings)
    return max(len(line) for line in lines), len(lines)


def render_frame(now: datetime, settings: Settings) -> str:
    """Return the multi-line frame for ``now`` (no trailing newline)."""
    lines = _compose(now, settings)
    width = max(len(line) for line in lines)

    cols = _term_columns()
    margin = (cols - width) // 2 if cols > width else 0
    out = "\n".join((" " * margin + line).rstrip() for line in lines)

    if settings.color:
        code = SGR_CODES.get(settings.color_name, SGR_CODES["cyan"])
        out = f"\x1b[{code}m{out}{RESET}"
    return out
