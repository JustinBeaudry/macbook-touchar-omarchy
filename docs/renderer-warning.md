# Misleading renderer fallback warning

## Confirmed — 2026-11-15

The notification reads: **“Touch Bar renderer failed — The selected renderer is unavailable. Using the built-in controls.”**

There is no custom `~/.config/t1bridge/renderer` on the affected machine. T1Bridge v0.1.12's launcher nevertheless tries to execute that path and sends the same fallback notification used for a broken custom renderer. It then runs its in-process built-in renderer. A successful notification also means the fallback message does not appear in the renderer journal.

This warning does **not** establish that the built-in renderer failed or explain the dark panel.

## Local messaging workaround

The existing user-local desktop provider's `notify_fallback()` now returns success without notifying for `selection-unavailable` **only when no selection file or symlink exists**. It resolves an absolute `XDG_CONFIG_HOME`, falling back to an absolute `$HOME/.config`, as the launcher does. Broken symlinks, existing non-executable selections and exited custom renderers retain their warnings.

A timestamped backup of the local provider was made first. Packaged files were not edited. Bash syntax validation and isolated function tests passed for absent selection, broken symlink and renderer exit. The user renderer was restarted.

**This fixes misleading messaging, not panel illumination.** Restore the backed-up provider to roll this messaging change back; preserve the independent keyboard-backlight fix.

## Separate panel investigation

- Rebinding only USB display interface `1-3:2.3` reinitialized the DRM driver, but the user still reported failure.
- A temporary 10-second hardware-service diagnostic trace reported successful display open, digitizer open, function-key input open, virtual keyboard creation, session watch and session admission.
- No frame-error record appeared in that window; this is not proof of USB update replies or illumination.
- The runtime diagnostic drop-in and user-manager diagnostic environment were removed afterward.

Upstream already documents a matching post-S3 dark-panel state on MacBookPro14,2: [display failure boundaries](https://github.com/standardagents/t1bridge/blob/v0.1.12/docs/display-failures.md) and [issue #18](https://github.com/standardagents/t1bridge/issues/18). The documented next experiment is bounded USB-reply observation, not speculative power writes or repeated resets.

Evidence: reviewed local notification text, absence of a custom selection, installed provider, bounded service diagnostics, and upstream v0.1.12 source (`crates/t1-touchbar/src/main.rs`, `renderer_launcher.rs`, and `docs/display-failures.md`). Raw notification history and journals are not published.
