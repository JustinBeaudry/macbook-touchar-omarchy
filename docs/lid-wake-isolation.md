# Lid wake isolation: first completed RTC interval

## Controlled result — 2026-11-15

The user authorized a lid-open RTC test with **only the lid device's wake permission temporarily disabled**. Normal RTC, power-button and built-in input wake permissions were not changed. No logind lid-close action, runtime-power setting, driver or authentication policy was modified.

Verified the local device as `/sys/bus/platform/devices/PNP0C0D:00`, firmware path `\_SB_.LID0`, with original `power/wakeup=enabled`. Saved that policy before changing it, and configured independent systemd restoration.

```text
23:10:37.582 LID0 wake temporarily disabled
23:10:37.594 RTC armed for 23:11:38
23:10:38.699 systemd-sleep began suspend operation
23:11:41.167 systemd-sleep returned
23:11:41.443 measured suspend clock gap: 54.134 seconds
23:11:41.443 scheduled time reached; RTC alarm no longer pending
23:11:41.443 original LID0 wake=enabled restored
```

The user subsequently confirmed: **“input was responsive, touch bar did not turn off.”** This establishes user-perceived responsiveness after the longer completed interval, while Touch Bar sleep power-off remains unresolved. The panel behavior is an observation, not a measured energy-consumption result.

## Comparison

- Previous instrumented, normal-wake-policy cycle: **2.925 s** measured suspended; RTC alarm still pending at early wake; lid device event/active counters increased.
- This lid-wake-disabled cycle: **54.134 s** measured suspended; resume completed after the scheduled wake time, and the RTC alarm was no longer pending.
- Earlier isolation of only Thunderbolt RP05/RP09 wake permission did not prevent early wake.

This is the strongest controlled lead so far that the **lid wake path contributes to premature wake in a lid-open suspend**. It is one successful intervention, not repeated reliability validation or proof that the physical lid sensor is faulty. Shared firmware wake routing and notifications during resume are not fully characterized.

The scheduled alarm is set before suspend preparation, so measured sleep residency is naturally shorter than the nominal timer interval; awake preparation/resume time is not included in the BOOTTIME-minus-MONOTONIC clock-gap measurement. Do not call the 54.134 s observation a failed one-minute timer test.

## Verified cleanup

Both normal and independent systemd cleanup completed. Subsequent read-only checks confirmed:

- Lid wake permission restored to `enabled`.
- RTC alarm empty.
- No permanent lid-wake setting installed.

The temporary state/commands do not alter whether closing the lid normally requests suspend. While disabled during the experiment, opening the lid would not itself have been an available wake method; this trade-off is why permanent disablement is not a default recommendation.

## Next steps and limits

1. User-perceived input responsiveness is confirmed for this longer cycle; Touch Bar remaining lit is also confirmed. Keep those outcomes separate.
2. Repeat the isolated timed test before adopting a workaround.
3. Preserve ordinary close-lid/open-lid behavior: do not globally disable lid wake without explicit acceptance of losing open-lid wake.
4. Research firmware/kernel lid-notification handling and, if justified, an opt-in policy that distinguishes already-open-lid explicit suspend from normal closed-lid suspend. That conditional policy has **not** been implemented or validated here.
5. Keep the input-delay and Touch Bar display-power issues distinct; a completed sleep interval does not by itself prove those problems are resolved.

Evidence: temporary test output, bounded suspend/logind journals and post-test sysfs/alarm checks. No input content, firmware tables or raw journals are published.
