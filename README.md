# cliclock

A terminal clock for Arch / Omarchy, written in Python 3 with only the standard library.

**Status:** early. The ASCII rendering is still a placeholder frame (one line of text); real digit fonts are not implemented yet. See [docs/INTERFACES.md](docs/INTERFACES.md) for the frozen contract.

## Install

### Arch / Omarchy package (system-wide)

```bash
git clone <repo> && cd cliclock && makepkg -si
cliclock --version
```

### User-level install (no root)

```bash
git clone <repo> && cd cliclock && ./install.sh
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
| `--settings [PATH]` | print the resolved settings, config path and whether the file exists, then exit; optional PATH selects the config file |
| `--set KEY=VALUE` | per-run settings override, repeatable (also works with `--settings`) |
| `--config PATH` | config file location override (wins over `--settings PATH`) |
| `--once` | render one frame and exit |
| `--version` | print `cliclock 0.1.0` |
| `--help` | show usage |

With no flags the clock runs until you press Ctrl-C (or send SIGTERM); it then exits with status 0.

```bash
cliclock                                  # run until Ctrl-C
cliclock --once                           # one frame, then exit
cliclock --set twelve_hour=true --set show_seconds=false
cliclock --settings --set color_name=green
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
| `digit_style` | `"block"`, `"slim"` |
| `twelve_hour` | `true`, `false` |
| `show_seconds` | `true`, `false` |
| `show_date` | `true`, `false` |
| `tick_style` | `"blink"`, `"cycle"` |
| `color` | `true`, `false` |
| `refresh_seconds` | number greater than 0 |
| `date_format` | non-empty `strftime` format string |
| `color_name` | `red`, `green`, `yellow`, `blue`, `magenta`, `cyan`, `white` (used when `color` is true) |

Precedence: defaults < config file < `--set`. Invalid values, unknown keys and malformed TOML print a one-line warning to stderr and fall back to the default.

There is no interactive settings menu yet: `--settings` just prints the resolved settings (sorted `key = value`), the config path and whether the file exists. Edit the TOML file by hand.

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
