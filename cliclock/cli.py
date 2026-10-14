"""Argument parsing and dispatch for cliclock."""

from __future__ import annotations

import argparse
import os
import signal
import sys
import time
from dataclasses import asdict, fields
from datetime import datetime
from pathlib import Path

from cliclock import __version__
from cliclock.config import (
    _CHOICES,
    Settings,
    _validate,
    config_path,
    default_settings,
    load_settings,
    save_settings,
)
from cliclock.render import render_frame

_CLEAR_SCREEN = "\x1b[2J\x1b[H"
_HIDE_CURSOR = "\x1b[?25l"
_SHOW_CURSOR = "\x1b[?25h"
_RESET_SGR = "\x1b[0m"


def build_parser() -> argparse.ArgumentParser:
    """Build the argparse parser."""
    p = argparse.ArgumentParser(
        prog="cliclock",
        description="A terminal clock. With no flags, runs the clock until Ctrl-C.",
    )
    p.add_argument(
        "--settings", nargs="?", const="", default=None, metavar="PATH",
        help="print the resolved settings, config path and whether the file "
        "exists, then exit. Optional PATH selects the config file. "
        "On a terminal this opens an interactive menu (see --no-menu).",
    )
    p.add_argument("--no-menu", action="store_true",
                   help="with --settings: never open the interactive menu, just print")
    p.add_argument("--save", action="store_true",
                   help="write the resolved settings (defaults < file < --set) to the config file")
    p.add_argument("--reset", action="store_true",
                   help="delete the config file and exit")
    p.add_argument(
        "--set", action="append", default=None, metavar="KEY=VALUE",
        help="per-run settings override (repeatable); also works with --settings",
    )
    p.add_argument("--config", metavar="PATH", help="config file location override")
    p.add_argument("--once", action="store_true",
                   help="render exactly one frame and exit (no loop)")
    hours = p.add_mutually_exclusive_group()
    hours.add_argument("--12h", dest="hours12", action="store_true",
                       help="use the 12-hour clock with AM/PM (overrides settings)")
    hours.add_argument("--24h", dest="hours24", action="store_true",
                       help="use the 24-hour clock (overrides settings)")
    p.add_argument("--version", action="version", version=f"cliclock {__version__}")
    return p


def _print_settings(settings: Settings, args: argparse.Namespace) -> None:
    path = config_path(args)
    for key, value in sorted(asdict(settings).items()):
        print(f"{key} = {value}")
    print(f"config path = {path}")
    print(f"config exists = {path.is_file()}")


_TRUE = ("true", "yes", "y", "1")
_FALSE = ("false", "no", "n", "0")
_HINTS = {"refresh_seconds": "number > 0, NUMBER", "date_format": "STRFTIME"}

_MENU_HELP = """\
  <number> or <key>  choose a setting, then type its new value (empty keeps it)
  s / save           save and quit
  d / defaults       reset every setting to its default (saved immediately)
  q / quit / empty   quit
  help / ?           show this help
Changes are saved as soon as they are made."""


def _fmt(value) -> str:
    return str(value).lower() if isinstance(value, bool) else str(value)


def _parse_menu_value(key: str, text: str):
    """Convert menu input to the field type and validate it (ValueError if bad)."""
    default = getattr(Settings(), key)
    if isinstance(default, bool):
        low = text.lower()
        if low in _TRUE:
            value = True
        elif low in _FALSE:
            value = False
        else:
            raise ValueError("must be true or false")
    elif isinstance(default, float):
        try:
            value = float(text)
        except ValueError:
            raise ValueError("must be a number") from None
    else:
        value = text
    return _validate(key, value)


def _print_menu(settings: Settings) -> None:
    print()
    for i, f in enumerate(fields(Settings), 1):
        if f.name in _CHOICES:
            hint = " | ".join(_CHOICES[f.name])
        elif isinstance(getattr(settings, f.name), bool):
            hint = "true | false"
        else:
            hint = _HINTS.get(f.name, "")
        line = f"  {i}. {f.name:<20} = {_fmt(getattr(settings, f.name)):<16}"
        print(f"{line} ({hint})" if hint else line.rstrip())
    print(f"  refresh = {settings.refresh_seconds}s")


def interactive_menu(settings: Settings, path: Path) -> int:
    """Interactive settings editor; returns the process exit code."""
    path = Path(path)
    names = [f.name for f in fields(Settings)]
    changed = False

    def save(msg: str) -> bool:
        try:
            save_settings(settings, path)
        except OSError as exc:
            print(f"cliclock: error: cannot write {path}: {exc.strerror or exc}",
                  file=sys.stderr)
            return False
        print(msg)
        return True

    print("cliclock settings")
    print(f"config: {path}" + ("" if path.is_file() else " (no file yet)"))
    _print_menu(settings)
    try:
        while True:
            choice = input("change [number|key]  s=save  d=defaults  q=quit> ").strip()
            low = choice.lower()
            if low in ("", "q", "quit"):
                if not changed:
                    print("cliclock: no changes")
                return 0
            if low in ("s", "save"):
                return 0 if save(f"cliclock: saved {path}") else 1
            if low in ("d", "defaults"):
                for name in names:
                    setattr(settings, name, getattr(default_settings(), name))
                if not save(f"cliclock: saved defaults to {path}"):
                    return 1
                changed = True
                _print_menu(settings)
                continue
            if low in ("help", "?"):
                print(_MENU_HELP)
                _print_menu(settings)
                continue
            if choice.isdigit() and 1 <= int(choice) <= len(names):
                key = names[int(choice) - 1]
            elif choice in names:
                key = choice
            else:
                print(f"cliclock: error: unknown setting '{choice}'")
                continue
            current = _fmt(getattr(settings, key))
            raw = input(f"new value for {key} [{current}]> ").strip()
            if not raw:
                print(f"cliclock: {key} unchanged")
                continue
            try:
                value = _parse_menu_value(key, raw)
            except ValueError as exc:
                print(f"cliclock: error: {key}: {exc}")
                continue
            setattr(settings, key, value)
            if not save(f"cliclock: saved {path}"):
                return 1
            changed = True
            _print_menu(settings)
    except (EOFError, KeyboardInterrupt):
        print()
        return 0


def _run_loop(settings: Settings) -> None:
    """Tick loop: redraw the frame in place once per ``refresh_seconds``.

    On a TTY the cursor is hidden and the frame is redrawn in place; when
    stdout is not a TTY one newline-terminated frame is printed per tick.
    The terminal (cursor visibility + SGR) is restored on every exit path.
    """
    tty = sys.stdout.isatty()
    out = sys.stdout
    try:
        if tty:
            out.write(_HIDE_CURSOR)
        while True:
            frame = render_frame(datetime.now(), settings)
            if tty:
                out.write(f"{_CLEAR_SCREEN}{frame}")
            else:
                out.write(frame + "\n")
            out.flush()
            # Sleep to the next multiple of the period so 1s ticks do not drift.
            period = settings.refresh_seconds
            time.sleep(max(0.01, period - (time.time() % period)))
    except BrokenPipeError:
        # Reader went away: stop quietly and silence the interpreter's final flush.
        try:
            os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())
        except (OSError, ValueError):
            pass
    finally:
        if tty:
            try:
                out.write(f"{_RESET_SGR}{_SHOW_CURSOR}\n")
                out.flush()
            except (BrokenPipeError, OSError):
                pass


def _raise_exit(signum, frame) -> None:
    raise SystemExit(0)


def main(argv: list[str] | None = None) -> int:
    """CLI entry point; returns the process exit code."""
    args = build_parser().parse_args(argv)
    path = config_path(args)
    if args.reset:
        try:
            if path.exists():
                path.unlink()
                print(f"cliclock: removed {path}")
            else:
                print(f"cliclock: no config file at {path}")
        except OSError as exc:
            print(f"cliclock: error: cannot remove {path}: {exc.strerror or exc}",
                  file=sys.stderr)
            return 1
        return 0
    settings = load_settings(args)
    if args.hours12:
        settings.twelve_hour = True
    elif args.hours24:
        settings.twelve_hour = False
    if args.save:
        try:
            save_settings(settings, path)
        except OSError as exc:
            print(f"cliclock: error: cannot write {path}: {exc.strerror or exc}",
                  file=sys.stderr)
            return 1
        if args.settings is not None:
            _print_settings(settings, args)
        print(f"cliclock: saved {path}")
        return 0
    if args.settings is not None:
        if not args.no_menu and sys.stdin.isatty() and sys.stdout.isatty():
            return interactive_menu(settings, path)
        _print_settings(settings, args)
        return 0
    if args.once:
        print(render_frame(datetime.now(), settings))
        return 0
    signal.signal(signal.SIGTERM, _raise_exit)
    try:
        _run_loop(settings)
    except KeyboardInterrupt:
        pass
    return 0
