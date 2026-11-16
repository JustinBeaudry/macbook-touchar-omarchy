# Instrumented early wake: lid notification is a lead

## One diagnostic cycle — 2026-11-15

The user authorized a single RTC-controlled, lid-open cycle with **no changes to wake permissions**. Only `pm_debug_messages` and `pm_print_times` were temporarily enabled. Their exact original values were saved, and ordinary plus independent systemd cleanup restored them afterward. No input content, SPI/USB payloads or broad ACPI debug data was captured.

The 60-second alarm remained pending after wake, confirming another early wake. The BOOTTIME-minus-MONOTONIC change measured **2.925 seconds suspended**, distinct from time spent awake in suspend/resume transitions. The full transient test service's wall-clock interval was longer; its CPU/monotonic runtime is not a measurement of sleep residency.

## Counter evidence

A one-second awake baseline showed no changes in the sampled counters. Across the subsequent suspend/resume:

| Counter | Delta |
| --- | --- |
| ACPI GPE 07 | +298 |
| ACPI GPE 17 | +2 |
| ACPI GPE 32 | +1 |
| ACPI GPE 33 | +1 |
| ACPI GPE 6F | +1 |
| ACPI SCI | +301 |
| Lid device `PNP0C0D:00` event_count | +1 |
| Lid device `PNP0C0D:00` active_count | +1 |

The lid was the **only wake-source device with changed counters in the common snapshot set**. Its `wakeup_count` did not increase. `/sys/power/pm_wakeup_irq` again returned ENODATA, so there is no positively identified wake IRQ.

Logind did not log a new lid-position transition during this cycle, and the current lid state read `open`. A notification reporting an already-open lid would not necessarily create a logind open/closed transition.

This makes a lid notification a leading candidate, **not proof of the initiating source**. Counters span preparation and resume, and firmware may send a notification as a consequence of waking. The GPE numbers have not all been mapped to this firmware's methods; do not label them as specific devices without that mapping.

## Source boundary

In the inspected upstream Linux source, normal ACPI lid resume initialization calls the lid-state updater without signalling a wake event, while a lid notification calls it with wake signalling enabled. This supports distinguishing a lid notification from a blanket assumption that every resume unconditionally increments this source. It still does not establish event ordering relative to the actual hardware wake, and the upstream source is not proof of an exact match to the installed Omarchy binary.

References, upstream Linux commit `aebb7274476403040d582c61478df8f4a7bf9cd3`:

- [Lid updater and notification path](https://github.com/torvalds/linux/blob/aebb7274476403040d582c61478df8f4a7bf9cd3/drivers/acpi/button.c#L423-L469)
- [Resume initialization](https://github.com/torvalds/linux/blob/aebb7274476403040d582c61478df8f4a7bf9cd3/drivers/acpi/button.c#L526-L545)

The local lid device is `/sys/bus/platform/devices/PNP0C0D:00`, firmware path `\_SB_.LID0`, with wake permission currently `enabled`.

## PM timings

The recorded resume phases completed in approximately:

- noirq resume: 122 ms;
- early resume: 0.9 ms;
- normal device resume: 665 ms.

The slowest matched individual resume callbacks included Broadcom Wi-Fi (~664 ms), T1 USB (~273 ms) and Intel graphics (~264 ms). Parallel callback times must not be summed as total resume time. These observations do not identify the early-wake source or account for every part of perceived screen/input latency.

## Cleanup verified

- `pm_debug_messages=0` and `pm_print_times=0`, matching their originals.
- This test's pending RTC alarm cleared; alarm read back empty.
- Transient diagnostic service finished and was collected.
- No wake permissions changed in this diagnostic. No SPI runtime-power override was added.

## Next causal test — not authorized or run by this note

With explicit user approval, temporarily disable **only LID0 wake permission** during one lid-open, RTC-controlled cycle, preserving RTC, power-button and built-in input wake paths. Save and restore the original setting with independent cleanup. Opening the lid would not wake the machine during that experiment; the RTC or a brief power-button press after the fallback interval would.

If it completes the timer interval, repeat before treating lid notifications as causal. If it still wakes early, retain the counter evidence but do not claim the lid was responsible. Do not permanently disable lid wake or change logind lid policy from this counter snapshot alone.
