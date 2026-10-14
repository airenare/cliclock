"""Smoke tests (stdlib unittest). Never touch the real ~/.config/cliclock."""

import contextlib
import io
import os
import sys
import tempfile
import unittest
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from cliclock.cli import build_parser, main  # noqa: E402
from cliclock.config import default_settings, load_settings  # noqa: E402
from cliclock.render import (  # noqa: E402
    FONTS, available_fonts, frame_size, glyph_lines, render_frame,
)


def run(argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            code = main(argv)
        except SystemExit as exc:
            code = exc.code
    return code, out.getvalue(), err.getvalue()


class SmokeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.cfg = os.path.join(self.tmp.name, "config.toml")

    def test_version(self):
        code, out, _ = run(["--version"])
        self.assertEqual(code, 0)
        self.assertEqual(out.strip(), "cliclock 0.2.0")

    def test_help(self):
        code, out, _ = run(["--help"])
        self.assertEqual(code, 0)
        for flag in ("--settings", "--set", "--config", "--version", "--once",
                     "--12h", "--24h", "--save", "--reset", "--no-menu"):
            self.assertIn(flag, out)

    def test_bare_settings(self):
        code, out, _ = run(["--settings", "--config", self.cfg])
        self.assertEqual(code, 0)
        self.assertIn("digit_style = block", out)
        self.assertIn(self.cfg, out)
        self.assertIn("config exists = False", out)

    def test_settings_with_path(self):
        Path(self.cfg).write_text("twelve_hour = true\n")
        code, out, _ = run(["--settings", self.cfg])
        self.assertEqual(code, 0)
        self.assertIn("twelve_hour = True", out)
        self.assertIn("config exists = True", out)

    def test_malformed_config_gives_defaults(self):
        Path(self.cfg).write_text("this is = = not toml [[[")
        args = build_parser().parse_args(["--config", self.cfg])
        with contextlib.redirect_stderr(io.StringIO()) as err:
            s = load_settings(args)
        self.assertEqual(s, default_settings())
        self.assertIn("warning", err.getvalue())

    def test_invalid_and_unknown_values(self):
        Path(self.cfg).write_text('digit_style = "huge"\nbogus = 1\nshow_date = "yes"\n')
        args = build_parser().parse_args(["--config", self.cfg])
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(load_settings(args), default_settings())

    def test_set_override(self):
        args = build_parser().parse_args(
            ["--config", self.cfg, "--set", "digit_style=slim"])
        self.assertEqual(load_settings(args).digit_style, "slim")

    def test_once(self):
        code, out, _ = run(["--once", "--config", self.cfg])
        self.assertEqual(code, 0)
        self.assertGreater(len(out.splitlines()), 1)

    def test_once_slim_no_color(self):
        code, out, _ = run(["--once", "--config", self.cfg, "--set",
                            "digit_style=slim", "--set", "color=false"])
        self.assertEqual(code, 0)
        self.assertGreater(len(out.splitlines()), 1)
        self.assertNotIn("\x1b", out)

    def test_once_12h_flag(self):
        code, out, _ = run(["--once", "--config", self.cfg, "--12h",
                            "--set", "color=false"])
        self.assertEqual(code, 0)
        self.assertRegex(out, r"AM|PM")
        code, out, _ = run(["--once", "--config", self.cfg, "--24h",
                            "--set", "color=false", "--set", "twelve_hour=true"])
        self.assertNotRegex(out, r"AM|PM")

    def test_12h_24h_exclusive(self):
        code, _, _ = run(["--12h", "--24h"])
        self.assertEqual(code, 2)

    def test_render_frame(self):
        frame = render_frame(datetime.now(), default_settings())
        self.assertIsInstance(frame, str)
        self.assertTrue(frame)


T = datetime(2026, 1, 2, 13, 5, 6)  # even second
T1 = datetime(2026, 1, 2, 13, 5, 7)  # odd second
T_EIGHTS = datetime(2026, 1, 2, 8, 8, 8)


def S(**kw):
    kw.setdefault("color", False)
    return replace(default_settings(), **kw)


class RenderTests(unittest.TestCase):
    def setUp(self):
        p = mock.patch("shutil.get_terminal_size",
                       return_value=os.terminal_size((100, 30)))
        p.start()
        self.addCleanup(p.stop)

    def test_determinism(self):
        for s in (S(), S(digit_style="slim", show_date=True)):
            self.assertEqual(render_frame(T, s), render_frame(T, s))

    def test_tick_changes_frame(self):
        for style in ("blink", "cycle"):
            s = S(tick_style=style)
            a, b = render_frame(T, s), render_frame(T1, s)
            self.assertNotEqual(a, b, style)
        s = S(tick_style="blink")
        self.assertEqual(len(render_frame(T, s).splitlines()),
                         len(render_frame(T1, s).splitlines()))

    def test_fonts(self):
        self.assertEqual(set(available_fonts()),
                         {"block", "slim", "thin", "led", "ghost", "tall"})
        for name, font in FONTS.items():
            for d in "0123456789:":
                self.assertIn(d, font, name)
            heights = {len(g) for g in font.values()}
            widths = {len(r) for g in font.values() for r in g}
            self.assertEqual(len(heights), 1, name)
            self.assertEqual(len(widths), 1, name)
        self.assertNotEqual(FONTS["block"]["8"], FONTS["slim"]["8"])
        self.assertEqual(glyph_lines("nope", "1"), glyph_lines("block", "1"))

    def test_structure(self):
        self.assertEqual(len(render_frame(T, S()).splitlines()), 5)
        self.assertEqual(len(render_frame(T, S(show_date=True)).splitlines()), 7)
        self.assertIn("Fri 02 Jan 2026", render_frame(T, S(show_date=True)))

    def test_weird_date_format(self):
        frame = render_frame(T, S(show_date=True, date_format="%Q%"))
        self.assertTrue(frame)

    def test_12h_and_seconds(self):
        pm = render_frame(T, S(twelve_hour=True))
        self.assertIn("PM", pm)
        expect = [glyph_lines("block", c)[0] for c in "01"]
        self.assertIn("  ".join(expect), pm.splitlines()[0])
        self.assertNotIn("PM", render_frame(T, S()))
        full = render_frame(T, S()).splitlines()[0]
        short = render_frame(T, S(show_seconds=False)).splitlines()[0]
        self.assertLess(len(short), len(full))

    def test_color(self):
        on = render_frame(T, S(color=True, color_name="red"))
        self.assertTrue(on.startswith("\x1b[31m"))
        self.assertTrue(on.endswith("\x1b[0m"))
        self.assertEqual(on.count("\x1b[0m"), 1)
        self.assertNotIn("\x1b", render_frame(T, S(color=False)))

    def test_frame_size_matches_every_font(self):
        expected_rows = {"block": 5, "slim": 5, "thin": 3, "led": 5, "ghost": 5, "tall": 7}
        for style, rows in expected_rows.items():
            for date in (False, True):
                s = S(digit_style=style, show_date=date, color=False)
                cols, height = frame_size(s)
                self.assertEqual(height, rows + (2 if date else 0), (style, date))
                for now in (T, T1, T_EIGHTS):
                    with mock.patch("cliclock.render._term_columns", return_value=0):
                        lines = render_frame(now, s).splitlines()
                    self.assertEqual(len(lines), height, style)
                    self.assertLessEqual(max(len(l) for l in lines), cols, style)

    def test_blank_row_between_digits_and_date(self):
        s = S(digit_style="block", show_date=True, color=False)
        with mock.patch("cliclock.render._term_columns", return_value=0):
            lines = render_frame(T, s).splitlines()
        self.assertEqual(lines[5], "")
        self.assertTrue(lines[6].strip())

    def test_size_hook_runs_only_when_env_set(self):
        from cliclock import cli
        with mock.patch.dict(os.environ, {}, clear=False), \
                mock.patch("cliclock.cli.subprocess.run") as run_:
            os.environ.pop("CLICLOCK_ON_SIZE", None)
            cli._notify_size(62, 7)
            run_.assert_not_called()
        with mock.patch.dict(os.environ, {"CLICLOCK_ON_SIZE": "fit --x"}), \
                mock.patch("cliclock.cli.subprocess.run") as run_:
            cli._notify_size(62, 7)
            self.assertEqual(run_.call_args[0][0], ["fit", "--x", "62", "7"])

    def test_no_trailing_newline_and_rectangular(self):
        for style in ("block", "slim"):
            frame = render_frame(T_EIGHTS, S(digit_style=style))
            self.assertFalse(frame.endswith("\n"))
        # Block "8" fills its full width on every row, so stripped lines match.
        frame = render_frame(T_EIGHTS, S(digit_style="block"))
        self.assertEqual(len({len(l) for l in frame.splitlines()}), 1)

    def test_tiny_terminals(self):
        for size in ((1, 1), (0, 0), (5, 5)):
            with mock.patch("shutil.get_terminal_size",
                            return_value=os.terminal_size(size)):
                frame = render_frame(T, S(show_date=True, twelve_hour=True))
            self.assertTrue(frame)
            self.assertFalse(frame.splitlines()[0].startswith(" "))


if __name__ == "__main__":
    unittest.main()
