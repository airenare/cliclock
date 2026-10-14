"""Settings dataclass plus TOML load/save. Never raises out of load_settings."""

from __future__ import annotations

import contextlib
import os
import sys
import tomllib
from dataclasses import asdict, dataclass, fields
from pathlib import Path
from typing import Any

COLOR_NAMES = ("red", "green", "yellow", "blue", "magenta", "cyan", "white")


def _default_config_path() -> Path:
    base = os.environ.get("XDG_CONFIG_HOME") or os.path.join(Path.home(), ".config")
    return Path(base) / "cliclock" / "config.toml"


DEFAULT_CONFIG_PATH: Path = _default_config_path()


@dataclass
class Settings:
    """All user-tunable options; the field names are the config-file keys."""

    digit_style: str = "block"  # "block" | "slim" | "thin" | "led" | "ghost" | "tall"
    twelve_hour: bool = False
    show_seconds: bool = True
    show_date: bool = False
    tick_style: str = "blink"  # "blink" | "cycle"
    color: bool = True
    refresh_seconds: float = 1.0
    date_format: str = "%a %d %b %Y"
    color_name: str = "cyan"  # one of COLOR_NAMES; used when color is true


_CHOICES: dict[str, tuple[str, ...]] = {
    "digit_style": ("block", "slim", "thin", "led", "ghost", "tall"),
    "tick_style": ("blink", "cycle"),
    "color_name": COLOR_NAMES,
}


def default_settings() -> Settings:
    """Return a Settings object with all defaults."""
    return Settings()


def _warn(msg: str) -> None:
    print(f"cliclock: warning: {msg}", file=sys.stderr)


def _validate(key: str, value: Any) -> Any:
    """Return the validated value for ``key`` or raise ValueError."""
    default = getattr(Settings(), key)
    if isinstance(default, bool):
        if not isinstance(value, bool):
            raise ValueError("must be true or false")
    elif isinstance(default, float):
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("must be a number")
        value = float(value)
        if not value > 0:
            raise ValueError("must be > 0")
    else:
        if not isinstance(value, str):
            raise ValueError("must be a string")
        if key in _CHOICES and value not in _CHOICES[key]:
            raise ValueError("must be one of " + ", ".join(_CHOICES[key]))
        if key == "date_format" and not value:
            raise ValueError("must not be empty")
    return value


def _coerce_text(key: str, text: str) -> Any:
    """Convert a ``--set`` string to the field's type (ValueError if bad)."""
    default = getattr(Settings(), key)
    if isinstance(default, bool):
        low = text.strip().lower()
        if low not in ("true", "false"):
            raise ValueError("must be true or false")
        return low == "true"
    if isinstance(default, float):
        try:
            return float(text)
        except ValueError:
            raise ValueError("must be a number") from None
    return text


def config_path(args=None) -> Path:
    """Resolve config path: --config > --settings PATH > XDG default."""
    explicit = getattr(args, "config", None)
    if explicit:
        return Path(explicit).expanduser()
    via_settings = getattr(args, "settings", None)
    if via_settings:
        return Path(via_settings).expanduser()
    return _default_config_path()


def load_settings(args=None) -> Settings:
    """Load settings: defaults < config file < ``--set`` overrides.

    Problems produce one-line stderr warnings and fall back per field.
    """
    settings = default_settings()
    names = {f.name for f in fields(Settings)}
    path = config_path(args)
    if path.is_file():
        try:
            with path.open("rb") as fh:
                data = tomllib.load(fh)
        except (tomllib.TOMLDecodeError, OSError, UnicodeDecodeError) as exc:
            _warn(f"cannot read {path}: {exc}; using defaults".replace("\n", " "))
            data = {}
        for key, value in data.items():
            if key not in names:
                _warn(f"{path}: unknown key '{key}' ignored")
                continue
            try:
                setattr(settings, key, _validate(key, value))
            except ValueError as exc:
                _warn(f"{path}: invalid {key}={value!r} ({exc}); using default")
    for item in getattr(args, "set", None) or []:
        key, sep, text = item.partition("=")
        key = key.strip()
        if not sep or key not in names:
            _warn(f"--set {item!r}: expected KEY=VALUE with a known key; ignored")
            continue
        try:
            setattr(settings, key, _validate(key, _coerce_text(key, text)))
        except ValueError as exc:
            _warn(f"--set {item!r}: {exc}; ignored")
    return settings


def _toml_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float):
        return repr(value)
    escaped = str(value).replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def save_settings(settings: Settings, path: Path | None = None) -> Path:
    """Write settings as TOML (creating parent dirs); return the path."""
    target = Path(path) if path is not None else _default_config_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"{k} = {_toml_value(v)}" for k, v in asdict(settings).items()]
    # Write to a sibling temp file and rename so a running clock never reads a half-written file.
    tmp = target.with_name(target.name + ".tmp")
    try:
        tmp.write_text("\n".join(lines) + "\n", encoding="utf-8")
        os.replace(tmp, target)
    except OSError:
        with contextlib.suppress(OSError):
            tmp.unlink()
        raise
    return target
