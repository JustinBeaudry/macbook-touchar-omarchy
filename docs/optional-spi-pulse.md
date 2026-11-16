# Optional SPI input wake pulse

**Experimental, opt-in.** For the verified MacBookPro14,2 setup only. This addresses delayed keyboard/trackpad input, separately from Touch Bar illumination. One attended temporary pulse trial passed, including user-confirmed input after an idle pause. Repeated reliability and energy cost remain unmeasured.

## Local installation status

Installed and verified on 2026-11-15: all three optional files are root-owned and match the repository copies; the effective suspend service queues the SPI service before Touch Bar recovery; the service has its independent restoration command configured. Unit verification passed with an unrelated existing NVMe-unit warning. The pulse unit is inactive pending its first automatic trigger, and both current power controls are `auto`. No pulse or sleep was triggered during installation. An attended sleep/wake under the installed integration is still pending.

## Install or add to an existing installation

Read [automatic recovery prerequisites and firmware limits](automatic-recovery.md) and [the research and evidence](spi-power-remediation-research.md) first.

```bash
python3 -m unittest discover -s tests -v
sudo bash install.sh --with-spi-pulse
```

The installer performs read-only checks and asks for `INSTALL`. It does not sleep, run a pulse, or call ACPI. Running the installer **without** `--with-spi-pulse` does not enable this feature on a new install; it also does not remove an already installed optional feature.

Additional root-owned files:

```text
/usr/local/libexec/macbook-spi-wake-pulse
/etc/systemd/system/macbook-spi-wake-pulse.service
/etc/systemd/system/systemd-suspend.service.d/80-macbook-spi-wake-pulse.conf
```

## Behavior and restoration

After `systemd-sleep suspend` returns, the optional drop-in asynchronously starts the pulse service. Its trigger is ordered before this repo's `90-` Touch Bar recovery drop-in, so the two recoveries can proceed concurrently. Nothing keeps running while idle.

The helper rechecks model, PCI `8086:9d2a` at `0000:00:1e.3`, and the keyboard's SPI parent. Before changing either runtime-power control it saves their **actual original values** in a private restoration record. It sets the parent and controller to `on` for **two seconds**, then restores those original values. On the tested machine both originals are `auto`; a pre-existing `on` policy is preserved, not silently changed.

Safety properties:

- No pre-suspend or permanent always-on SPI override.
- No driver reload, input grab, key logging, screen-lock or authentication change.
- Systemd serializes starts of the same oneshot service; an existing state file is not overwritten.
- `finally` restores after ordinary helper errors. A **separate `ExecStopPost` process** also restores after failure, termination or timeout of the pulse process, including SIGKILL.
- Five-second start and stop timeouts, no restart loop. Firmware/kernel hangs still cannot be guaranteed recoverable by a userspace timeout.
- State lives under root-owned, mode-0700 `/run/macbook-spi-wake-pulse`, with a mode-0600 record containing only allowlisted target labels and original policy values. It contains no arbitrary writable paths.
- A failed restoration retains the record for investigation/retry. Journals expose failures; they are not proof of physical input recovery.

Keeping normal idle runtime PM avoids the persistent policy change we were concerned about. It does **not** establish zero extra energy use or fix the underlying kernel behavior.

## Verify after an ordinary attended sleep/wake

```bash
journalctl -b -u macbook-spi-wake-pulse.service --no-pager -n 40
cat /sys/bus/pci/devices/0000:00:1e.3/power/control
cat /sys/bus/pci/devices/0000:00:1e.3/pxa2xx-spi.3/power/control
```

For this machine the controls should return to `auto` after two seconds. Check input immediately and after a 15-second idle pause. Do not start the service repeatedly on a healthy panel merely to test installation. Do not restart `systemd-suspend.service`: that puts the machine to sleep.

## Disable only this optional feature

From the same checkout revision used for installation:

```bash
sudo bash install.sh --uninstall-spi-pulse
```

The installer removes the trigger first, reloads systemd, stops the pulse service (invoking its restoration), retries saved-state restoration if necessary, then removes only matching SPI feature files. It leaves Touch Bar illumination recovery installed. Changed files or restoration failures cause refusal rather than blind deletion.

To remove both recoveries: `sudo bash install.sh --uninstall`.

If restoration is reported incomplete, inspect the journal and, while the helper is still installed, retry only the saved-state restoration:

```bash
sudo /usr/local/libexec/macbook-spi-wake-pulse --restore
```

Do not delete the saved state until its original settings have been restored. `/run` and the runtime sysfs settings reset at reboot; this is not a substitute for investigating a failure.

## Tests and remaining validation

All **40 tests** in the combined standard-library suite passed locally. Coverage includes model/device/hierarchy gates, exact original-policy preservation, errors and partial writes, malformed/symlinked/oversized state, overlapping-pulse refusal, independent restoration after SIGKILL of a synthetic worker, and systemd cleanup/trigger configuration. Synthetic tests use only temporary files, not real input or power hardware.

A separate transient user-unit test also confirmed that systemd executes `ExecStopPost` after an actual unit start timeout, using only a sleep command and temporary marker file. Unit configuration verification passed, with an unrelated warning from an existing NVMe suspend unit. Neither test establishes physical SPI recovery under the installed unit.

The packaged automatic integration still requires its own attended sleep/wake test after installation. Do not promote the optional feature to a default or generalize model support from one temporary hardware trial.
