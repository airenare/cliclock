"""Packaging tests (stdlib unittest, offline). Installs only into temp dirs."""

import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import cliclock  # noqa: E402


class PackagingTests(unittest.TestCase):
    def test_bash_syntax(self):
        for name in ("install.sh", "uninstall.sh", "PKGBUILD"):
            r = subprocess.run(["bash", "-n", str(ROOT / name)],
                               capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, f"{name}: {r.stderr}")

    def test_executables(self):
        for rel in ("install.sh", "uninstall.sh", "packaging/cliclock"):
            self.assertTrue(os.access(ROOT / rel, os.X_OK), rel)
        first = (ROOT / "packaging" / "cliclock").read_text().splitlines()[0]
        self.assertEqual(first, "#!/usr/bin/env python3")

    def test_pkgver_matches_version(self):
        text = (ROOT / "PKGBUILD").read_text()
        m = re.search(r"^pkgver=(\S+)$", text, re.M)
        self.assertIsNotNone(m)
        self.assertEqual(m.group(1), cliclock.__version__)

    def test_install_run_uninstall(self):
        with tempfile.TemporaryDirectory() as tmp:
            prefix = os.path.join(tmp, "prefix")
            home = os.path.join(tmp, "home")
            env = dict(
                os.environ,
                HOME=home,
                XDG_CONFIG_HOME=os.path.join(home, ".config"),
                PATH=os.path.join(prefix, "bin") + os.pathsep + os.environ["PATH"],
            )
            env.pop("SUDO_USER", None)

            def sh(*args):
                return subprocess.run(args, env=env, cwd="/",
                                      capture_output=True, text=True)

            r = sh("bash", str(ROOT / "install.sh"), "--prefix", prefix)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            exe = os.path.join(prefix, "bin", "cliclock")
            r = sh(exe, "--version")
            self.assertEqual((r.returncode, r.stdout.strip()),
                             (0, "cliclock 0.1.0"), r.stderr)
            r = sh(exe, "--once")
            self.assertEqual(r.returncode, 0, r.stderr)
            for _dirpath, dirs, files in os.walk(os.path.join(prefix, "lib", "cliclock")):
                self.assertNotIn("__pycache__", dirs)
                self.assertFalse([f for f in files if f.endswith(".pyc")])
            self.assertFalse(os.path.exists(os.path.join(home, ".config")))

            r = sh("bash", str(ROOT / "install.sh"), "--uninstall", "--prefix", prefix)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertFalse(os.path.exists(exe))
            self.assertFalse(os.path.exists(os.path.join(prefix, "lib", "cliclock")))

    def test_unknown_flag_exits_2(self):
        r = subprocess.run(["bash", str(ROOT / "install.sh"), "--bogus"],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 2)


if __name__ == "__main__":
    unittest.main()
