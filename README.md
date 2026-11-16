# MacBook Touch Bar

Field notes and local workarounds for the Apple T1 Touch Bar on a MacBookPro14,2 running Arch Linux / Omarchy. This is a troubleshooting notebook, not a replacement driver or firmware distribution.

## Status

| Area | Status |
| --- | --- |
| Keyboard backlight dims when touching controls | Confirmed provider bug; local workaround previously user-tested |
| Touch Bar stays blank after suspend/resume | Manual and automatic recovery confirmed; repeated reliability unverified |
| Keyboard/trackpad unresponsive after wake | SPI workaround removed; one short lid-open suspend felt fast with normal power-saving; longer controlled validation needed |
| Earlier firmware recovery | Not reconstructed; no reproducible recovery claim |

## Automatic wake recovery

**Only MacBookPro14,2 with the exact firmware-table fingerprint verified here.** Other models/firmware are refused. Requires working T1Bridge and loaded `acpi_call`; this does not install drivers. ACPI calls can hang affected machines—read [support limits, safety and rollback](docs/automatic-recovery.md) first.

```bash
git clone https://github.com/JustinBeaudry/macbook-touchar-omarchy.git
cd macbook-touchar-omarchy
python3 -m unittest discover -s tests -v
sudo bash install.sh
```

Installation does not put the machine to sleep or call firmware. To remove: `sudo bash install.sh --uninstall` from the same revision.

### Optional: faster keyboard/trackpad response after wake

A separate, **experimental opt-in** pulses SPI runtime power for two seconds, then restores the original settings—no permanent always-on override:

```bash
sudo bash install.sh --with-spi-pulse
```

Read [safety, evidence and SPI-only rollback](docs/optional-spi-pulse.md) first. One temporary trial passed, but the first installed automatic cycle still had about 10 seconds of input delay. This is **not yet a reliable input-delay fix**. Default installation leaves it off.

## Notes

- [Automatic recovery: installation, safety, logs and uninstall](docs/automatic-recovery.md)
- [SPI keyboard/trackpad wake-delay comparison](docs/spi-input-wake-delay.md)
- [Lower-power remediation research and proposed tests](docs/spi-power-remediation-research.md)
- [Optional two-second SPI pulse: install and rollback](docs/optional-spi-pulse.md)
- [Transition bracket results and prompt raw input despite perceived delay](docs/transition-bracket-results.md)
- [USB input comparison and lid-event/re-suspend evidence](docs/usb-input-comparison.md)
- [Fast lid-open suspend and sleep-duration caveat](docs/lid-open-comparison.md)

- [Confirmed post-sleep wake recovery](docs/confirmed-wake-recovery.md)
- [Keyboard-backlight HUD fix](docs/keyboard-backlight.md)
- [Misleading renderer warning and diagnostic findings](docs/renderer-warning.md)
- [Suspend/resume investigation and recovery ladder](docs/suspend-resume.md)
- [Observed environment and evidence](docs/environment.md)

## Earlier renderer-only recovery attempt

From the affected desktop user's session:

```bash
systemctl --user restart t1-touchbar.service
```

This did **not** recover the observed post-sleep dark panel; see the confirmed wake recovery above. An `active` service does **not** prove that the panel or touch input works. Test the controls physically and record the result. The optional installer above adds the separate confirmed wake sequence, not repeated service restarts.

## Upstream projects

- [T1Bridge](https://github.com/standardagents/t1bridge): installed hardware service, renderer and drivers.
- [t1-revive](https://github.com/niconistal/t1-revive): separate recovery tooling; an existing local checkout is not evidence that a particular recovery procedure was used.

## Publishing policy

Keep firmware, fingerprints, keybags, credentials, raw journals, serial numbers, personal paths and device-specific network identifiers out of this repository. Publish reviewed summaries and narrowly scoped patches, not machine dumps. Instructions here describe observed versions; check current package behavior before applying a workaround.
