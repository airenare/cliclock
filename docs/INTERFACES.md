# cliclock interface contract (frozen)

Downstream tasks are written against this document.

> **render.py must implement `render_frame(now, settings) -> str`; config.py must keep `load_settings`/`save_settings` signatures and the Settings field names stable.**

## config.py

```python
DEFAULT_CONFIG_PATH: Path            # ~/.config/cliclock/config.toml (respect $XDG_CONFIG_HOME)

@dataclass
class Settings:
    digit_style: str = "block"       # "block" | "slim"
    twelve_hour: bool = False
    show_seconds: bool = True
    show_date: bool = False
    tick_style: str = "blink"        # "blink" | "cycle"
    color: bool = True
    refresh_seconds: float = 1.0
    date_format: str = "%a %d %b %Y"
    color_name: str = "cyan"         # extra; red|green|yellow|blue|magenta|cyan|white, used when color is true

def default_settings() -> Settings
def load_settings(args=None) -> Settings      # args: parsed argparse Namespace (or None)
def save_settings(settings: Settings, path: Path | None = None) -> Path
def config_path(args=None) -> Path            # --config > --settings PATH > XDG default
```

### Allowed values

| field | type | allowed |
|---|---|---|
| `digit_style` | str | `block`, `slim` |
| `twelve_hour` | bool | true/false |
| `show_seconds` | bool | true/false |
| `show_date` | bool | true/false |
| `tick_style` | str | `blink`, `cycle` |
| `color` | bool | true/false |
| `refresh_seconds` | float | > 0 (TOML integers accepted) |
| `date_format` | str | non-empty `strftime` format |
| `color_name` | str | `red green yellow blue magenta cyan white` |

### Behaviour of `load_settings`

Precedence: defaults < config file < `--set` overrides. If the file is absent, defaults are used silently. Malformed TOML, unknown keys, wrong types or out-of-range values print a one-line `cliclock: warning: ...` to stderr and fall back to the default for that field (whole file on malformed TOML). Unknown keys are ignored. It never raises. `--set` values are parsed per field type (`true`/`false` for bools, a number for floats). `save_settings` writes TOML, creating parent directories, and returns the path (default: XDG path).

### Config file format (TOML)

```toml
digit_style = "block"
twelve_hour = false
show_seconds = true
show_date = false
tick_style = "blink"
color = true
refresh_seconds = 1.0
date_format = "%a %d %b %Y"
color_name = "cyan"
```

## render.py

```python
def render_frame(now: datetime, settings: Settings) -> str   # multi-line frame, no trailing newline
def render_placeholder(now: datetime, settings: Settings) -> str  # stub: one line
```

`render_frame` is currently a delegator to `render_placeholder`. The CLI calls only `render_frame`.

## cli.py

`main(argv=None) -> int`

| flag | meaning |
|---|---|
| (none) | run loop: one frame per `refresh_seconds` until Ctrl-C / SIGTERM (exit 0). Cursor and SGR are reset on exit |
| `--settings [PATH]` | print resolved settings (sorted `key = value`), `config path = ...`, `config exists = True/False`; exit 0. Optional PATH is the config file. Never prompts. A future interactive menu extends this flag |
| `--set KEY=VALUE` | repeatable per-run override; works with `--settings` |
| `--config PATH` | config file location; wins over `--settings PATH` |
| `--once` | render one frame, print it with a newline, exit 0 |
| `--version` | print `cliclock 0.1.0`, exit 0 |
| `--help` | usage, exit 0 |

Loop output: on a TTY each tick is `\r` + clear-line + frame (no newline); when stdout is not a TTY each frame is printed with a trailing newline. The follow-up render task owns real redraw-in-place logic.
