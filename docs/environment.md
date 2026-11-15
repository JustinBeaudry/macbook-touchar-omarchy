# Observed environment

Snapshot from 2026-11-15; not a compatibility guarantee.

| Component | Observed value |
| --- | --- |
| Hardware | Apple MacBookPro14,2, T1 Touch Bar |
| OS | Arch Linux / Omarchy |
| Kernel | `7.2.15-1-omarchy` |
| Omarchy | `4.5.0-3` |
| t1bridge | `0.1.12-1` |
| t1bridge-dkms | `0.1.12-1` |
| t1bridge-omarchy | `0.2.2-1` |
| Hardware service | System `t1-touchbar-hw.service` |
| Renderer | User `t1-touchbar.service` |
| Keyboard LED | `/sys/class/leds/spi::kbd_backlight` (maximum 255) |

## Service boundaries

The hardware service owns the device and exposes a Unix socket. The user renderer runs within the graphical session. The installed Omarchy integration selects a desktop provider via a systemd drop-in; a later user drop-in selects the local keyboard-backlight fix.

The packaged renderer unit has graphical-session ordering and the Omarchy drop-in requires `WAYLAND_DISPLAY`. The hardware service has `Restart=on-failure`; an apparently live but unresponsive process will not be restarted merely because the panel stops working.

These observations do not establish which layer is responsible for the resume incident.

## Evidence and limits

- Current package versions: `pacman -Q`.
- Service definitions: `systemctl cat t1-touchbar-hw.service` and `systemctl --user cat t1-touchbar.service`.
- State: process start times, device/socket listings and bounded system/user journals.
- Prior confirmed brightness fix: local curated note `wiki/macbook-touchbar-keyboard-backlight-fix.md`, lines 24–136.
- An existing `t1-revive` checkout and local firmware files were found, but earlier recovery actions were not reconstructed. Firmware is deliberately not included or published.

No full system dump, archived private session, biometric data or firmware payload is part of this repository.
