# cliclock

A terminal clock for Arch / Omarchy, written in Python 3 with only the standard library.

Big ASCII digits (`block`, `slim`, `thin`, `led`, `ghost` and `tall` fonts), an animated colon (`blink` or `cycle`), 12/24-hour display, an optional date line and colour, plus an interactive settings menu. See [docs/INTERFACES.md](docs/INTERFACES.md) for the frozen contract.

![cliclock in the block style](docs/images/screenshot.png)

## Install

### Arch / Omarchy package (system-wide)

```bash
git clone https://github.com/airenare/cliclock.git && cd cliclock && makepkg -si
cliclock --version
```

### User-level install (no root)

```bash
git clone https://github.com/airenare/cliclock.git && cd cliclock && ./install.sh
cliclock --version
```

If `~/.local/bin` is not on your `PATH`, the installer warns you; add this to your shell profile:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

`sudo ./install.sh` installs system-wide into `/usr/local` instead. `./install.sh --prefix DIR` picks any other prefix. Nothing is written outside the prefix; your config directory is never touched.

### What gets installed where

| item | user install (`~/.local`) | `sudo ./install.sh` | `makepkg -si` |
|---|---|---|---|
| launcher | `~/.local/bin/cliclock` | `/usr/local/bin/cliclock` | `/usr/bin/cliclock` |
| package | `~/.local/lib/cliclock/cliclock/*.py` | `/usr/local/lib/cliclock/cliclock/*.py` | `/usr/lib/cliclock/cliclock/*.py` |
| README | `~/.local/lib/cliclock/README.md` | `/usr/local/lib/cliclock/README.md` | `/usr/lib/cliclock/README.md` |
| docs | `~/.local/lib/cliclock/docs/INTERFACES.md` | `/usr/local/lib/cliclock/docs/INTERFACES.md` | `/usr/lib/cliclock/docs/INTERFACES.md` |

## Uninstall

```bash
./uninstall.sh          # user-level install
sudo ./uninstall.sh     # /usr/local install
sudo pacman -R cliclock # package install
```

Manually, for the user-level install: `rm -f ~/.local/bin/cliclock && rm -rf ~/.local/lib/cliclock`. Your config file is left alone.

## Usage

| flag | meaning |
|---|---|
| (none) | run the clock until Ctrl-C |
| `--settings [PATH]` | on a terminal, open the interactive settings menu; otherwise (or with `--no-menu`) print the resolved settings, config path and whether the file exists. Optional PATH selects the config file |
| `--no-menu` | with `--settings`: never open the menu, just print |
| `--save` | write the resolved settings (defaults < config file < `--set`) to the config file |
| `--reset` | delete the config file and exit |
| `--set KEY=VALUE` | per-run settings override, repeatable (also works with `--settings`) |
| `--config PATH` | config file location override (wins over `--settings PATH`) |
| `--once` | render one frame and exit |
| `--12h` / `--24h` | force the 12-hour (with AM/PM) or 24-hour clock for this run; mutually exclusive |
| `--version` | print `cliclock 0.1.0` |
| `--help` | show usage |

With no flags the clock runs until you press Ctrl-C (or send SIGTERM); it then exits with status 0.

```bash
cliclock                                  # run until Ctrl-C
cliclock --once                           # one frame, then exit
cliclock --set twelve_hour=true --set show_seconds=false
cliclock --12h --set digit_style=slim
cliclock --set tick_style=cycle --save   # persist the choice
cliclock --settings                       # interactive menu on a terminal
cliclock --reset                          # delete the config file
```

## Settings

The config file is `$XDG_CONFIG_HOME/cliclock/config.toml`, or `~/.config/cliclock/config.toml` if `XDG_CONFIG_HOME` is unset. A missing file is fine; defaults are used. All nine fields with their defaults:

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

| field | allowed values |
|---|---|
| `digit_style` | `"block"`, `"slim"`, `"thin"`, `"led"`, `"ghost"`, `"tall"` |
| `twelve_hour` | `true`, `false` |
| `show_seconds` | `true`, `false` |
| `show_date` | `true`, `false` |
| `tick_style` | `"blink"`, `"cycle"` |
| `color` | `true`, `false` |
| `refresh_seconds` | number greater than 0 |
| `date_format` | non-empty `strftime` format string |
| `color_name` | `red`, `green`, `yellow`, `blue`, `magenta`, `cyan`, `white` (used when `color` is true) |

Precedence: defaults < config file < `--set`. Invalid values, unknown keys and malformed TOML print a one-line warning to stderr and fall back to the default.

### Digit fonts

Selected with `digit_style`: `block` is big 5-row digits drawn with `██`; `slim` is narrow 5-row ASCII digits (`|`, `_`, `#`, `o`); `thin` is compact 3-row box-drawing digits; `led` is a dot matrix (`●` lit, `·` unlit); `ghost` is `▓` digits over a faint `░` background; `tall` is large 7-row digits, 5 columns wide per glyph.

If the environment variable `CLICLOCK_ON_SIZE` is set, the live clock runs `$CLICLOCK_ON_SIZE COLS ROWS` once at start so a launcher can fit its window to the chosen font (ignored when unset; failures are ignored).

### Settings menu

`cliclock --settings` opens a menu when both stdin and stdout are terminals. Piped or redirected runs (or `--no-menu`) print the plain settings block and never prompt.

```
cliclock settings
config: /home/you/.config/cliclock/config.toml (no file yet)
  1. digit_style           = block            (block | slim | thin | led | ghost | tall)
  ...
change [number|key]  s=save  d=defaults  q=quit>
```

- Type a setting's number or name, then its new value. An empty value keeps the current one.
- Every accepted change is saved immediately. Bad values print an error and nothing is saved.
- `s` save and quit, `d` reset all settings to defaults (saved), `q` or an empty line quit, `?` help.
- Booleans accept `true/false/yes/no/y/n/1/0`.
- Ctrl-D / Ctrl-C quit cleanly; earlier changes stay saved.

## Development

Run from a checkout without installing:

```bash
./bin/cliclock            # dev launcher, works from any directory
python3 -m cliclock       # from the repo root
```

Tests:

```bash
python3 -m unittest discover -s tests -v
```

## Requirements

Python 3.11 or newer (standard library only, including `tomllib`). No other runtime dependencies.

## Hyprland launcher (optional)

`contrib/hyprland/` has two helper scripts for a small floating Ghostty window that fits the clock:

- `cliclock-window [cliclock args]` opens the window, e.g. `cliclock-window --set digit_style=tall`.
- `cliclock-fit-window COLS ROWS` is called by cliclock itself (through `CLICLOCK_ON_SIZE`) to resize and centre the window for the chosen font, so the padding stays equal on all four sides.

Copy both to a directory on your `PATH` and bind the launcher, for example in a Lua Hyprland config: `hl.bind("SUPER + SHIFT + code:53", hl.dsp.exec_cmd("cliclock-window"))`. The pixel metrics are calibrated for Ghostty font size 14; edit `CELL_W`, `CELL_H` and `OVERHEAD` in `cliclock-fit-window` if yours differ. The scripts use Hyprland's Lua dispatcher syntax and need `hyprctl`, `jq` and `ghostty`.

## License

MIT, see [LICENSE](LICENSE).
