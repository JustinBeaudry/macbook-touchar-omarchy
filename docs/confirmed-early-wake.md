# Genuine early wake during corrected RTC test

## Outcome — 2026-11-15

The user ran the lid-open test without the DasKeyboard, reported waking after roughly seven seconds, observed everything switch off, and confirmed instantly responsive input afterward.

Unlike the preceding invalid RTC attempt, the corrected controller **kept its alarm armed until the observed sleep transition ended**. Its asynchronous-transition logic had first passed a synthetic test with no hardware access.

## Timing and alarm evidence

```text
22:31:18.066 alarm armed for 22:32:19
22:31:18.074 suspend request queued; alarm retained
22:31:19.175 systemd-sleep began suspend operation
22:31:31.374 systemd-sleep returned
22:31:31.650 logind suspend operation finished
22:31:31.709 controller confirmed alarm still pending; flagged EARLY WAKE
22:31:31.709 controller cleared only its own pending alarm
```

The systemd-sleep operation lasted about **12.199 s including transitions**, and resume completed roughly 47 s before the scheduled alarm. The user's approximate seven seconds can describe a different perceived interval; exact S3 residency was not measured.

This is a real early-wake observation, **not a completed 60-second sleep** and not another instance of prematurely clearing the alarm. The scheduled RTC alarm was still pending after wake, so it was not the trigger. The cause remains unidentified.

The user did not want further USB-keyboard comparison. Only built-in activity timing was observed, without key codes, text, passwords or coordinates. First fresh keyboard/trackpad activity occurred 1.551/2.665 s after the observer resumed; those are activity timestamps, not exact hardware-ready times. User confirmation establishes the perceived immediate responsiveness.

## Read-only wake-source investigation

- `/sys/power/pm_wakeup_irq` returned ENODATA, providing no specific wake IRQ.
- Available wake-source counters had no before/after baseline identifying the trigger.
- ACPI wakeup status showed `RP05` and `RP09` enabled, mapped to PCI root ports `0000:00:1c.4` and `0000:00:1d.0`.
- `XHC2`/`XHC3` were already disabled. `LID0`, `SPIT`, and PCH `XHC1` were enabled.
- Both SPI runtime-power controls remained `auto`; the experimental SPI pulse remained removed.
- The RTC alarm was checked empty after cleanup. Confirmed Touch Bar wake recovery remained installed and acknowledged its wake sequence.

[Omarchy #12194](https://github.com/omacom/omarchy/issues/12194) reports spontaneous Alpine Ridge wakes on the same MacBookPro14,2 generation and identifies the Thunderbolt root-port wake paths as a remediation candidate. It involves another kernel/version and does not prove the source of this wake. Its untested or broad recommendations must not be copied wholesale.

## RP05/RP09 controlled trial — early wake persisted

The user authorized and performed one temporary test. Verified PCI root ports `8086:9d14` and `8086:9d18`, class `060400`, at the expected addresses, each with an Alpine Ridge `8086:15d2` descendant. Both original wake permissions were `enabled`.

- Wake permission on only those two root ports was set to `disabled`, with readback confirmation. Runtime power policies and RTC/lid/power-button/built-in input wake paths were not changed.
- At `22:40:53.790`, the RTC was armed for `22:41:54`.
- The normal suspend operation ran from `22:40:54.893` to `22:41:06.278`, including transitions.
- At `22:41:06.574`, the controller flagged another early wake with the requested interval incomplete. The user independently reported waking after a few seconds.
- Both original wake permissions were restored to `enabled` and the test's own pending RTC alarm cleared. Independent systemd cleanup also completed. Read-only checks confirmed restoration and an empty alarm.

**Disabling RP05/RP09 wake permission alone did not prevent early wake.** Do not persist that change as a demonstrated fix or claim it rules out every Thunderbolt/platform-related mechanism.

## Next diagnostic proposal — not yet run

Stop changing wake policies without attribution. The kernel exposes ACPI GPE counters, suspend statistics and optional PM debug/per-device timing (`pm_debug_messages` and `pm_print_times`, both currently `0`). The specific wake IRQ remains unavailable. Suspend statistics report no recorded callback failures, which does not identify the wake source or exclude a firmware issue.

The previously inspected local SSDT6 maps PCH `XHC1` to GPE `0x6D`. PCH USB and the T1 USB device still allow wake, as does built-in SPI input; these are leads only. No before/after counter delta yet identifies which event caused early wake.

With new authorization, collect a before/after ACPI/wakeup-source snapshot and clock-gap measurement in one attended RTC cycle, optionally enabling only bounded PM timing/debug messages and restoring their exact original values afterward. Do not record SPI/USB payloads or keyboard content. Change no wake permissions during that diagnostic. A real clock-gap measurement is needed to separate time in sleep from long transition time.

Do not add `pcie_port_pm=off`, disable all wake sources, blacklist Thunderbolt, or change the sleep mode on the strength of the current evidence. No wake-source settings were changed during this read-only investigation.

## Panel-power caveat

The user observed all displays switch off in this cycle, unlike the previous report that the Touch Bar stayed lit. That variation is recorded, not treated as proof that the full Touch Bar sleep-power lifecycle is fixed or that sleep energy use has been measured.
