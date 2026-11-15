# Touch Bar on Omarchy

Field notes and local workarounds for the Apple T1 Touch Bar on a MacBookPro14,2 running Arch Linux / Omarchy. This is a troubleshooting notebook, not a replacement driver or firmware distribution.

## Status

| Area | Status |
| --- | --- |
| Keyboard backlight dims when touching controls | Confirmed provider bug; local workaround previously user-tested |
| Touch Bar stops responding around suspend/resume | Open; renderer restart attempted, visual confirmation pending |
| Earlier firmware recovery | Not reconstructed; no reproducible recovery claim |

## Notes

- [Keyboard-backlight HUD fix](docs/keyboard-backlight.md)
- [Suspend/resume investigation and recovery ladder](docs/suspend-resume.md)
- [Observed environment and evidence](docs/environment.md)

## Quick recovery attempt

From the affected desktop user's session:

```bash
systemctl --user restart t1-touchbar.service
```

This only restarts the renderer. An `active` service does **not** prove that the panel or touch input works. Test the controls physically and record the result. No automatic resume workaround is installed by this repository.

## Upstream projects

- [T1Bridge](https://github.com/standardagents/t1bridge): installed hardware service, renderer and drivers.
- [t1-revive](https://github.com/niconistal/t1-revive): separate recovery tooling; an existing local checkout is not evidence that a particular recovery procedure was used.

## Publishing policy

Keep firmware, fingerprints, keybags, credentials, raw journals, serial numbers, personal paths and device-specific network identifiers out of this repository. Publish reviewed summaries and narrowly scoped patches, not machine dumps. Instructions here describe observed versions; check current package behavior before applying a workaround.
