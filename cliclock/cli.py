"""Argument parsing and dispatch for cliclock."""

from __future__ import annotations

import argparse
import signal
import sys
import time
from dataclasses import asdict
from datetime import datetime

from cliclock import __version__
from cliclock.config import Settings, config_path, load_settings
from cliclock.render import render_frame

_CLEAR_LINE = "\x1b[2K"
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
        "(An interactive settings menu will extend this flag later.)",
    )
    p.add_argument(
        "--set", action="append", default=None, metavar="KEY=VALUE",
        help="per-run settings override (repeatable); also works with --settings",
    )
    p.add_argument("--config", metavar="PATH", help="config file location override")
    p.add_argument("--once", action="store_true",
                   help="render exactly one frame and exit (no loop)")
    p.add_argument("--version", action="version", version=f"cliclock {__version__}")
    return p


def _print_settings(settings: Settings, args: argparse.Namespace) -> None:
    path = config_path(args)
    for key, value in sorted(asdict(settings).items()):
        print(f"{key} = {value}")
    print(f"config path = {path}")
    print(f"config exists = {path.is_file()}")


def _run_loop(settings: Settings) -> None:
    """Minimal tick loop; real redraw-in-place logic is a follow-up task."""
    tty = sys.stdout.isatty()
    try:
        while True:
            frame = render_frame(datetime.now(), settings)
            if tty:
                sys.stdout.write(f"\r{_CLEAR_LINE}{frame}")
            else:
                sys.stdout.write(frame + "\n")
            sys.stdout.flush()
            time.sleep(settings.refresh_seconds)
    finally:
        if tty:
            sys.stdout.write(f"{_RESET_SGR}{_SHOW_CURSOR}\n")
            sys.stdout.flush()


def _raise_exit(signum, frame) -> None:
    raise SystemExit(0)


def main(argv: list[str] | None = None) -> int:
    """CLI entry point; returns the process exit code."""
    args = build_parser().parse_args(argv)
    settings = load_settings(args)
    if args.settings is not None:
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
