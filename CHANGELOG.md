# Changelog

## 0.2.0

- Four new digit styles: `thin`, `led`, `ghost` and `tall`.
- A blank row between the digits and the date (or AM/PM).
- Hot reload: the running clock picks up config changes on the next tick.
- The clock draws on the terminal's alternate screen, so no scrollback builds up.
- `CLICLOCK_ON_SIZE` hook, plus Hyprland helper scripts in `contrib/hyprland/` that size and centre the window for the chosen style.
- Config saves are atomic.
- The `slim` font draws 0 and 8 with the same `#` pixels as the other digits.

## 0.1.0

- First release: `block` and `slim` fonts, blinking or cycling separator, 12/24-hour display, optional date and colour, interactive settings menu, TOML config, user-level installer and PKGBUILD.
