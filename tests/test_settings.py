"""Settings persistence and interactive menu tests. Only touch tempfile dirs."""

import builtins
import contextlib
import io
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from cliclock.cli import interactive_menu, main  # noqa: E402
from cliclock.config import default_settings, load_settings  # noqa: E402


def run(argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            code = main(argv)
        except SystemExit as exc:
            code = exc.code
    return code, out.getvalue(), err.getvalue()


def menu(settings, path, script):
    out, err = io.StringIO(), io.StringIO()
    with mock.patch.object(builtins, "input", side_effect=script), \
            contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = interactive_menu(settings, path)
    return code, out.getvalue(), err.getvalue()


class _TmpCase(unittest.TestCase):
    def setUp(self):
        self._td = tempfile.TemporaryDirectory()
        self.addCleanup(self._td.cleanup)
        self.path = Path(self._td.name) / "sub" / "config.toml"
        self.cfg = ["--config", str(self.path)]


class PersistenceTests(_TmpCase):
    def test_set_save_then_settings(self):
        code, out, _ = run(["--set", "digit_style=slim", "--save", *self.cfg])
        self.assertEqual(code, 0)
        self.assertIn(f"cliclock: saved {self.path}", out)
        code, out, _ = run(["--settings", "--no-menu", *self.cfg])
        self.assertEqual(code, 0)
        self.assertIn("digit_style = slim", out)
        self.assertIn("config exists = True", out)

    def test_regeneration_after_delete(self):
        run(["--set", "digit_style=slim", "--save", *self.cfg])
        self.path.unlink()
        code, out, _ = run(["--settings", *self.cfg])
        self.assertEqual(code, 0)
        self.assertIn("digit_style = block", out)
        self.assertIn("config exists = False", out)

    def test_malformed_toml(self):
        self.path.parent.mkdir(parents=True)
        self.path.write_text("digit_style = [oops\n")
        code, out, err = run(["--settings", *self.cfg])
        self.assertEqual(code, 0)
        self.assertIn("digit_style = block", out)
        self.assertIn("warning", err)
        self.assertNotIn("Traceback", err)

    def test_invalid_file_value_falls_back_per_field(self):
        self.path.parent.mkdir(parents=True)
        self.path.write_text('digit_style = "huge"\ntick_style = "cycle"\n')
        code, out, err = run(["--settings", *self.cfg])
        self.assertEqual(code, 0)
        self.assertIn("warning", err)
        self.assertIn("digit_style = block", out)
        self.assertIn("tick_style = cycle", out)

    def test_invalid_set_value(self):
        code, out, err = run(["--set", "digit_style=huge", "--settings", *self.cfg])
        self.assertEqual(code, 0)
        self.assertIn("warning", err)
        self.assertNotIn("Traceback", err)
        self.assertIn("digit_style = block", out)

    def test_reset(self):
        run(["--save", *self.cfg])
        self.assertTrue(self.path.is_file())
        code, out, _ = run(["--reset", *self.cfg])
        self.assertEqual(code, 0)
        self.assertIn(f"cliclock: removed {self.path}", out)
        self.assertFalse(self.path.exists())
        code, out, _ = run(["--reset", *self.cfg])
        self.assertEqual(code, 0)
        self.assertIn(f"cliclock: no config file at {self.path}", out)


class MenuTests(_TmpCase):
    def test_happy_path(self):
        code, out, err = menu(default_settings(), self.path, ["1", "slim", "q"])
        self.assertEqual(code, 0)
        self.assertIn("cliclock settings", out)
        self.assertIn("(no file yet)", out)
        self.assertIn("1. digit_style", out)
        self.assertIn("9. color_name", out)
        self.assertIn(f"cliclock: saved {self.path}", out)
        self.assertIn('digit_style = "slim"', self.path.read_text())
        self.assertEqual(load_settings(_Args(self.path)).digit_style, "slim")

    def test_rejects_bad_value(self):
        code, out, err = menu(default_settings(), self.path, ["1", "huge", "q"])
        self.assertEqual(code, 0)
        self.assertIn("cliclock: error: digit_style:", out)
        self.assertNotIn("Traceback", out + err)
        self.assertFalse(self.path.exists())
        self.assertIn("cliclock: no changes", out)

    def test_unknown_key_and_key_name_selection(self):
        s = default_settings()
        code, out, _ = menu(s, self.path, ["bogus", "tick_style", "cycle", "q"])
        self.assertIn("cliclock: error: unknown setting 'bogus'", out)
        self.assertEqual(s.tick_style, "cycle")

    def test_bool_parsing(self):
        s = default_settings()
        _, out, _ = menu(s, self.path, ["show_date", "yes", "color", "NO", "twelve_hour", "maybe", "q"])
        self.assertTrue(s.show_date)
        self.assertFalse(s.color)
        self.assertFalse(s.twelve_hour)
        self.assertIn("cliclock: error: twelve_hour: must be true or false", out)

    def test_float_and_empty_keep(self):
        s = default_settings()
        _, out, _ = menu(s, self.path, ["refresh_seconds", "abc", "refresh_seconds", "", "refresh_seconds", "0.5", "q"])
        self.assertIn("cliclock: error: refresh_seconds: must be a number", out)
        self.assertIn("cliclock: refresh_seconds unchanged", out)
        self.assertEqual(s.refresh_seconds, 0.5)

    def test_defaults_and_eof(self):
        s = default_settings()
        s.show_date = True
        code, out, _ = menu(s, self.path, ["d", EOFError()])
        self.assertEqual(code, 0)
        self.assertIn(f"cliclock: saved defaults to {self.path}", out)
        self.assertFalse(s.show_date)

    def test_save_failure_returns_1(self):
        blocker = Path(self._td.name) / "file"
        blocker.write_text("x")
        code, out, err = menu(default_settings(), blocker / "c.toml", ["s"])
        self.assertEqual(code, 1)
        self.assertIn("cliclock: error: cannot write", err)

    def test_menu_not_entered_without_tty(self):
        with mock.patch.object(builtins, "input", side_effect=AssertionError("prompted")):
            code, out, _ = run(["--settings", *self.cfg])
        self.assertEqual(code, 0)
        self.assertIn("config exists = False", out)


class _Args:
    def __init__(self, path):
        self.config = str(path)
        self.settings = None
        self.set = None


if __name__ == "__main__":
    unittest.main()


class HotReloadTests(_TmpCase):
    def _args(self, *extra):
        from cliclock.cli import build_parser
        return build_parser().parse_args([*self.cfg, *extra])

    def test_reload_picks_up_valid_edit(self):
        from cliclock.cli import _reload_settings
        run(["--set", "digit_style=slim", "--save", *self.cfg])
        run(["--set", "digit_style=tall", "--save", *self.cfg])
        fresh = _reload_settings(self._args())
        self.assertEqual(fresh.digit_style, "tall")

    def test_reload_ignores_invalid_file_quietly(self):
        from cliclock.cli import _reload_settings
        self.path.parent.mkdir(parents=True)
        for bad in ('digit_style = ', 'digit_style = "nope"\n', 'bogus = 1\n'):
            self.path.write_text(bad)
            err = io.StringIO()
            with contextlib.redirect_stderr(err):
                self.assertIsNone(_reload_settings(self._args()), bad)
            self.assertEqual(err.getvalue(), "")

    def test_reload_keeps_cli_overrides(self):
        from cliclock.cli import _reload_settings
        run(["--set", "digit_style=slim", "--save", *self.cfg])
        fresh = _reload_settings(self._args("--set", "digit_style=led", "--12h"))
        self.assertEqual(fresh.digit_style, "led")
        self.assertTrue(fresh.twelve_hour)

    def test_loop_applies_reload_and_resizes_window(self):
        from cliclock import cli
        from cliclock.config import default_settings, save_settings
        self.path.parent.mkdir(parents=True)
        s = default_settings()
        s.digit_style, s.color = "thin", False
        save_settings(s, self.path)
        ticks = []

        class Stop(Exception):
            pass

        def fake_sleep(_):
            ticks.append(1)
            if len(ticks) == 1:
                tall = default_settings()
                tall.digit_style, tall.color = "tall", False
                save_settings(tall, self.path)
            elif len(ticks) == 3:
                raise Stop

        out = io.StringIO()
        out.isatty = lambda: False
        sizes = []
        with mock.patch.object(cli.time, "sleep", fake_sleep), \
                mock.patch.object(cli, "_notify_size", lambda c, r: sizes.append((c, r))), \
                mock.patch.object(cli.sys, "stdout", out):
            with self.assertRaises(Stop):
                cli._run_loop(s, self.path, lambda: cli._reload_settings(self._args()))
        text = out.getvalue()
        self.assertIn("┌", text)       # first frame: thin
        self.assertIn("█", text)       # after the edit: tall
        # non-tty mode never calls the window hook
        self.assertEqual(sizes, [])

    def test_save_is_atomic_and_leaves_no_temp_file(self):
        from cliclock.config import default_settings, save_settings
        save_settings(default_settings(), self.path)
        self.assertEqual([p.name for p in self.path.parent.iterdir()], ["config.toml"])
