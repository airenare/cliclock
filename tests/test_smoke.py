"""Smoke tests (stdlib unittest). Never touch the real ~/.config/cliclock."""

import contextlib
import io
import os
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from cliclock.cli import build_parser, main  # noqa: E402
from cliclock.config import default_settings, load_settings  # noqa: E402
from cliclock.render import render_frame  # noqa: E402


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
        self.assertEqual(out.strip(), "cliclock 0.1.0")

    def test_help(self):
        code, out, _ = run(["--help"])
        self.assertEqual(code, 0)
        for flag in ("--settings", "--set", "--config", "--version", "--once"):
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
        self.assertEqual(len(out.splitlines()), 1)

    def test_render_frame(self):
        frame = render_frame(datetime.now(), default_settings())
        self.assertIsInstance(frame, str)
        self.assertTrue(frame)


if __name__ == "__main__":
    unittest.main()
