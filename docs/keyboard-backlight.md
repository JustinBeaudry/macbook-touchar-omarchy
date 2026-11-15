# Keyboard-backlight HUD bug

## Confirmed finding — 2026-11-13

The keyboard backlight hardware worked. Setting `spi::kbd_backlight` to 50% lit the keys, but using Touch Bar controls could reduce the level again.

In `t1bridge-omarchy 0.2.2-1`, the packaged `desktop-provider` calls:

```bash
percent=$(omarchy-brightness-keyboard status) || exit 1
```

On the observed Omarchy version, `status` is not supported. Unknown arguments enter the brightness-down branch, reducing the level by a step rather than reading it. Displaying the HUD therefore changes brightness.

The installed files were compared again on 2026-11-15; this mismatch remains present.

## Local workaround

Preserve the packaged provider and modify a user-local copy:

```bash
mkdir -p "$HOME/.local/lib/t1bridge"
# Only do this on first setup; do not overwrite an existing customized provider.
cp -n /usr/lib/t1bridge-omarchy/desktop-provider "$HOME/.local/lib/t1bridge/desktop-provider"
```

Replace only `show_keyboard_backlight()` in that copy with:

```bash
show_keyboard_backlight() {
  # Read the level without changing it while displaying the OSD.
  local device current maximum percent
  for device in /sys/class/leds/*kbd_backlight*; do
    [[ -r $device/brightness && -r $device/max_brightness ]] || continue
    current=$(<"$device/brightness")
    maximum=$(<"$device/max_brightness")
    [[ $current =~ ^[0-9]+$ && $maximum =~ ^[0-9]+$ ]] || continue
    (( maximum > 0 )) || continue
    percent=$(( current * 100 / maximum ))
    omarchy-osd -i keyboard -p "$percent"
    return
  done
  return 1
}
```

Create `~/.config/systemd/user/t1-touchbar.service.d/90-local-provider.conf` with the following, replacing `/absolute/home/path` with your actual home directory (do not use `$HOME` or `~` inside `Environment=`):

```ini
[Service]
Environment=T1BRIDGE_DESKTOP_PROVIDER=/absolute/home/path/.local/lib/t1bridge/desktop-provider
```

Validate and apply:

```bash
bash -n "$HOME/.local/lib/t1bridge/desktop-provider"
systemctl --user daemon-reload
systemctl --user restart t1-touchbar.service
```

## Verification

The original test observed brightness **128 before and 128 after** invoking the patched `v1 show-keyboard-backlight` operation. The user confirmed the controls worked. This is historical confirmation of the brightness workaround, not proof of suspend/resume reliability.

Read-only state checks:

```bash
brightnessctl -d 'spi::kbd_backlight' get
systemctl --user show t1-touchbar.service -p ActiveState -p Environment
```

## Maintenance and rollback

The copied provider does not inherit package updates. Compare it with `/usr/lib/t1bridge-omarchy/desktop-provider` after upgrades. Remove the drop-in only once the packaged implementation is safe, then reload the user manager and restart the renderer. Removing it while the package remains affected can reintroduce the dimming bug.

## Evidence

Historical source: local curated note `wiki/macbook-touchbar-keyboard-backlight-fix.md`, lines 24–136 (confirmed diagnosis, workaround and user verification). Current comparison: installed packaged provider versus the existing local override, plus `/usr/bin/omarchy-brightness-keyboard`, inspected 2026-11-15. No raw session or firmware archive was used.
