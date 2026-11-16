# Keyboard/trackpad delay after wake: SPI runtime-power comparison

## Outcome — 2026-11-15

The Touch Bar relit automatically, but the user reported that the visible lock screen initially ignored both keyboard and trackpad. They confirmed they moved the trackpad and tapped Shift immediately and continuously after wake, with no response until the screen blanked and then input became usable.

A timing-only evdev observer recorded fresh activity independently of the lock-screen UI. It did not grab input or log key codes, values, password text or pointer coordinates. Observations were relative to when the observer resumed executing after suspend, not absolute device-ready measurements.

| Condition | First fresh keyboard activity | First fresh trackpad activity |
| --- | --- | --- |
| Original runtime-power settings (`auto`) | 12.246 s | 10.622 s |
| SPI PCI parent and controller temporarily `on` | 0.003 s | 0.114 s |

The user confirmed the second cycle was **“Much better this time.”**

This is one baseline and one intervention cycle, not repeated reliability validation. It supports a runtime-power-management contribution on the SPI path, but does not isolate which of the two devices needs the override. The systemd-sleep periods also differed: 53.568 s for the baseline versus 11.032 s for the intervention (including transition time). Comparable-duration repeats are needed before attributing the full improvement to the power settings.

## Temporary intervention

Validated the model as MacBookPro14,2, PCI vendor/device as `8086:9d2a`, and the keyboard's SPI device as a descendant of the expected controller. Temporarily changed only:

```text
/sys/bus/pci/devices/0000:00:1e.3/power/control
/sys/bus/pci/devices/0000:00:1e.3/pxa2xx-spi.3/power/control
```

Both started as `auto` with runtime status `suspended`. Both were set to `on` and checked as `active` before the attended sleep/wake. Both original values were automatically restored after the 30-second post-resume observation window; a separate read confirmed both were back at `auto`.

No persistent SPI power override was installed. No keyboard driver reload, input grab, authentication change, or lock-screen modification was made.

## Separate from Touch Bar illumination

During the improved-input cycle, the existing Touch Bar recovery again completed successfully about 0.28 seconds after systemd-sleep returned. The input power experiment did not replace or modify that recovery.

The screen-blanking observation suggested investigating the SPI path because Omarchy's blanking sequence also writes the keyboard backlight, whose commands use that controller. This was an investigation hypothesis, not proof that the backlight command itself caused recovery.

An Omarchy sleep-inhibitor restart error also appeared around wake. Its presence did not establish it as the input-delay cause; authentication was not weakened to address it.

## Follow-up

The user raised battery concerns before authorizing persistence. [Remediation research](spi-power-remediation-research.md) recommends testing a short wake-only pulse, then a transition-only bracket if needed, while retaining normal idle autosuspend. Do not install a persistent override by default from this one comparison. Awake-idle battery cost has not been measured, and keeping a child active may also keep its parent active. Validate comparable-duration repeated cycles and battery behavior; do not apply a broad PCI/USB power-saving disable.

Evidence: local timing-only input observation, bounded suspend-service logs, sysfs identity/power-state reads, and user confirmation. Raw input content and full logs are intentionally not published.
