# cliclock

A terminal clock.

## Why Python 3 + stdlib + ANSI

cliclock uses Python 3.11+ with only the standard library (`argparse`, `tomllib`, `dataclasses`, `datetime`) and plain ANSI escape codes. There are no dependencies and no build step, and Python 3 ships on Arch/OMARCHY, so the launcher runs straight from a checkout.

## Install / run

```bash
./bin/cliclock            # dev launcher, works from any cwd
python3 -m cliclock       # equivalent
```

`python3 -m cliclock` needs the project root on `PYTHONPATH` when run from another directory; `bin/cliclock` has no such requirement.

To get a bare `cliclock` command, put `bin/` on your `PATH` or symlink `bin/cliclock` into `~/.local/bin`.

## Usage

| flag | meaning |
|---|---|
| (none) | run the clock until Ctrl-C |
| `--settings [PATH]` | print resolved settings, config path and whether it exists; optional PATH picks the config file. An interactive menu will extend this flag later |
| `--set KEY=VALUE` | per-run override, repeatable (also with `--settings`) |
| `--config PATH` | config file location override |
| `--once` | render one frame and exit |
| `--version` | print `cliclock 0.1.0` |
| `--help` | show usage |

Default config: `$XDG_CONFIG_HOME/cliclock/config.toml` (else `~/.config/cliclock/config.toml`).

Tests: `python3 -m unittest discover -s tests -v`

## Interfaces

See [docs/INTERFACES.md](docs/INTERFACES.md) for the frozen contract.

## Not implemented yet

- Real ASCII digit fonts (`render_frame` is a one-line placeholder)
- Ticking animation (colon blink/cycle, redraw in place)
- Interactive settings menu
