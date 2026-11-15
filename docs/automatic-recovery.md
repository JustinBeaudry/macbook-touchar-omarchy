# Install automatic post-suspend recovery

A small local workaround for the post-sleep dark Touch Bar, **not a general MacBook driver installer**. The combined wake sequence was physically confirmed once on the machine described below. One automatic sleep/wake recovery was subsequently user-confirmed; repeated-cycle reliability and overall wake latency remain unvalidated.

**Local installation verified on 2026-11-15:** the helper and drop-in are root-owned, match the repository copies, and appear in the effective suspend service configuration. Systemd unit verification passed, with an unrelated warning from the pre-existing NVMe suspend unit. No sleep/wake test was triggered during installation.

## First automatic cycle — 2026-11-15

The user confirmed recovery after a normal sleep/wake, but reported slow wake time. The suspend-service journal shows:

- Return from system sleep: `17:50:43.588`.
- User slice thawed: `17:50:43.601`.
- Helper's initial power-byte read: `17:50:43.772` (`0x01`).
- `SOCW(1)` acknowledged: `17:50:43.855` (`0x0`).
- Awake report/readback complete: `17:50:43.873` (`0x02`).
- Suspend service complete: `17:50:43.882`.

The recovery completed about **0.285 seconds after systemd-sleep returned**, including about **83 ms** between the initial read and ACPI acknowledgement. It did not hit the discovery retry delay or 12-second timeout. Kernel logs around resume also contain PCIe D3 power-state failures, Thunderbolt warnings and T1 USB descriptor timeouts; these are investigation leads, not a proven attribution of the user's perceived delay. Whole-screen versus Touch Bar latency still needs clarification. No power-policy or driver change was made in response to the report.

## Supported hardware — intentionally narrow

- Apple **MacBookPro14,2**, T1 in USB configuration 2 (`05ac:8600`).
- ACPI device `APP7777:00` at `\_SB_.PCI0.XHC1.RHUB.ASOC`.
- **Exact verified SSDT6 SHA-256:** `38c8858a41c0aa3636fb995593e70cb7bdc9c839655ce422547ba8d4ddc580d1`.
- Arch Linux / Omarchy with systemd, Python 3, coreutils, and a working T1Bridge installation.
- `acpi_call` already installed and loaded (`/proc/acpi/call` exists). On this machine Omarchy already supplies its module-load configuration.

A model name alone is insufficient. Another firmware-table fingerprint is refused before any ACPI call. A firmware update may disable the workaround safely until the new table is reviewed. Do not remove the fingerprint check to get an unsupported machine past installation.

The observed cohort is T1Bridge 0.1.12-1, Omarchy 4.5.0-3 and kernel 7.2.15-1-omarchy. Other package versions have not been physically validated here. Check whether upstream has fixed resume before retaining the workaround after upgrades.

## Install

Read the scripts before giving them root access. Save work before the first sleep/wake test: ACPI firmware methods can hang affected machines, and a timeout cannot kill a call stuck in the kernel.

```bash
git clone https://github.com/JustinBeaudry/macbook-touchar-omarchy.git
cd macbook-touchar-omarchy
python3 -m unittest discover -s tests -v
sudo bash install.sh
```

The installer runs a **read-only** compatibility check, refuses to overwrite differing files, describes the changes, and asks you to type `INSTALL`. It does **not** invoke sleep or the wake method. Re-running installation with identical files is supported.

For unattended installation after reviewing the code and accepting the same risk, `sudo bash install.sh --yes` skips only the confirmation, not the compatibility gates.

Installed files, both root-owned:

```text
/usr/local/libexec/macbook-touchbar-wake
/etc/systemd/system/systemd-suspend.service.d/90-macbook-touchbar-wake.conf
```

There is no polling process, automatic reboot, package replacement, firmware flashing or Touch ID/keybag modification. This does not install or configure T1Bridge, drivers or `acpi_call` for you.

## How it runs

The systemd drop-in adds an `ExecStartPost` to **systemd-suspend.service**, so recovery runs after `systemd-sleep suspend` returns. It does not run at boot, on screen blanking, or from the separate hibernate services. It does not depend on deprecated `/etc/systemd/system-sleep` hook discovery.

The helper rechecks model, firmware fingerprint and ACPI device path each time. It waits up to five seconds for a unique display HID interface, reads its power byte, evaluates `SOCW(1)` exactly once, and requires a `0x0` result before sending a display-awake report if needed. It never sends `SOCW(0)` or the hardware-reset method. It does not retry firmware calls or report writes.

The command has a 12-second userspace timeout plus a two-second kill grace. A failed command is logged but does not make the suspend service fail (`ExecStartPost=-...`). Firmware/kernel hangs remain a real limitation; the timeout is not a hard guarantee against those.

## Inspect and test

```bash
# Read-only compatibility check:
sudo /usr/local/libexec/macbook-touchbar-wake --check

# Inspect integration (do NOT restart this service as an installation test):
systemctl cat systemd-suspend.service

# After an ordinary attended sleep/wake:
journalctl -b -u systemd-suspend.service --no-pager -n 60
```

**Do not run `systemctl restart systemd-suspend.service` to apply changes: it suspends the machine.** The installer only uses `daemon-reload`.

When ready, save your work, sleep through your normal desktop controls, wake, and physically check the Touch Bar. A `0x0` ACPI result and awake-byte readback do not prove illumination. Record physical outcome and repeated-cycle counts separately. No unattended suspend loop is provided.

For an explicitly approved manual recovery in an existing post-suspend dark state only:

```bash
sudo timeout --signal=TERM --kill-after=2s 12s /usr/local/libexec/macbook-touchbar-wake --wake
```

Do not experiment with firmware methods on an already healthy panel or another model.

## Uninstall / rollback

From the same revision used for installation:

```bash
sudo bash install.sh --uninstall
```

This removes only the two known files when their contents match the checkout and reloads systemd. It performs no sleep or ACPI call. If files were changed, it refuses removal so you can inspect them first. Empty parent directories may remain.

No wake-state change needs to be undone. The separate keyboard-backlight and notification workarounds are not installed or removed by this installer.

## Unsupported hardware

A refusal is intentional. Review the firmware method and upstream model-specific evidence before proposing support. Share only model, relevant package versions, firmware-table fingerprint and reviewed findings—not entire firmware tables, serials, raw journals, keybags or fingerprints. Do not call `FRST` or bypass the model/hash checks.

See [the physically confirmed manual recovery](confirmed-wake-recovery.md), [the investigation](suspend-resume.md), and [upstream issue #18](https://github.com/standardagents/t1bridge/issues/18).
