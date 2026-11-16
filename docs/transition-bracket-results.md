# Transition bracket did not reliably eliminate perceived unresponsiveness

## Attended trials — 2026-11-15

A temporary system service held the validated SPI PCI parent and controller at `on` before suspend and for two seconds after its observer detected resume. It then restored their actual original `auto` values. The installed wake-only SPI pulse was suppressed during each controlled trial; Touch Bar illumination recovery remained enabled. Independent systemd cleanup restored settings and removed the temporary suppression.

| Trial | First fresh keyboard activity | First fresh trackpad activity | User report |
| --- | --- | --- | --- |
| First bracket | 0.641 s | 0.982 s | “felt…okay”; requested repetition |
| Repeat bracket | 1.055 s | 0.747 s | still about 10 s of unresponsiveness |

These times are relative to a root system-service observer resuming execution, not the earlier user-slice observer's anchor. Direct numerical comparisons across those observer placements need that caveat.

## Critical boundary in the repeat

- Lid opened: `20:45:05.490`.
- Root observer detected resume at the same time.
- Fresh trackpad event observed: `20:45:06.236`.
- User slice thawed: `20:45:06.435`.
- Fresh keyboard event observed: `20:45:06.544` (about 0.11 s after thaw).
- SPI controls restored to `auto`: `20:45:07.506`.
- Password authentication succeeded and lock screen unlocked: approximately `20:45:10.764`.

The user-reported roughly 10-second delay is a perceived interaction delay, not a stopwatch measurement. The logged unlock is about 5.27 s after lid-open; these observations do not establish exactly how long the UI ignored input or how much time was spent entering the password.

Fresh input reached evdev promptly in this repeat while the user still reported an unresponsive UI. A theory that the physical input devices delivered no events throughout the entire perceived delay is therefore insufficient for this cycle. Compositor/seat delivery, lock-screen focus/blanking and other software resume behavior remain investigation candidates—not confirmed causes.

The sleep-lock inhibitor service also logged a refused inhibitor and restarted. That is a known Omarchy issue, but correlation alone does not establish it as the interaction-delay cause. The installed lock view already includes focus-restoration logic, so an older focus bug report must not be treated as proof that the identical source defect is present here.

## Disposition

- The bracket is **not** established as a reliable fix. Do not ship it or a persistent always-on override as the default.
- Both temporary trial settings were restored to `auto` and the temporary service/override cleaned up. The previously installed optional wake-only pulse remains installed; it is not promoted to a validated latency fix.
- No authentication weakening, driver reload, permanent runtime-PM disable or new sleep-mode policy was introduced.
- Normal input operation and prompt evdev delivery do not suggest a straightforward permanently failed keyboard/trackpad. They do not rule out every hardware/firmware defect either.
- The matching-model software report [Omarchy #17790](https://github.com/omacom/omarchy/issues/17790) remains relevant context, not a diagnosis of this exact machine.

Recommended next isolation: consider removing the unproven optional SPI pulse while retaining confirmed Touch Bar illumination recovery; compare wired USB input versus built-in input on the lock screen, with user authorization. If both fail together while raw events arrive, prioritize compositor/seat/lock-screen instrumentation. If only the built-ins fail, return to the SPI input path. A later alternate-OS comparison can help distinguish Linux-specific behavior from a hardware/firmware issue, but no OS change has been performed.

Evidence: timing-only evdev observation, bounded system/user journals and explicit user reports. No key codes, passwords, pointer coordinates or raw journals are published.
