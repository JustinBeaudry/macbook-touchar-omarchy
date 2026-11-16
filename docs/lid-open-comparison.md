# Lid-open explicit suspend: fast response, short-cycle caveat

## Outcome — 2026-11-15

After removing the experimental SPI pulse and reconnecting the DasKeyboard, the user confirmed **“Very fast response time”** from one explicit `systemctl suspend` test with the lid left open.

Configuration:

- Confirmed Touch Bar illumination recovery remained installed and ran successfully.
- Optional SPI wake-pulse helper/unit/trigger were removed and verified absent.
- Both SPI runtime-power policies remained `auto`.
- DasKeyboard and built-in input were monitored by the same timing-only observer. No input grab, key codes, characters, passwords or coordinates were logged.

## Validated request and timing

The preceding menu attempt generated no logind suspend request and no observed sleep cycle, so it was not a resume test. The retry used a visible terminal that waited for the user to press Enter before issuing exactly one normal `systemctl suspend` request, with the lid left open.

```text
21:48:50.180 logind received systemctl suspend request
21:48:51.286 systemd-sleep began suspend operation
21:49:01.778 systemd-sleep returned
21:49:01.791 user slice thawed
21:49:02.038 Touch Bar awake report acknowledged
21:49:02.048 logind suspend operation finished
```

There were no lid open/close transitions in this cycle. The systemd-sleep operation lasted about **10.492 seconds**, including transition time—not the intended one-minute test. This is a useful fast-cycle observation, not a controlled comparison against longer lid-close sleeps.

The observer first saw USB keyboard activity 1.768 s after it resumed, then built-in keyboard/trackpad activity at 6.244/6.641 s. The instructed procedure tested USB first and built-ins afterward; these timestamps are activity-arrival observations, not independent device-ready latencies. The user's explicit report establishes perceived responsiveness, not an exact millisecond response time.

The DasKeyboard descriptors disappeared later in the observation window. No cause was established, and its connection state after the user's comparison must not be assumed.

## Interpretation

- A permanent SPI runtime-PM disable is not justified by this fast cycle: input was responsive while normal idle policies were retained.
- A straightforward permanently failed built-in keyboard/trackpad is not the leading explanation for the observations, including USB-wide perceived freezes on another run.
- Lid-switch/queued-suspend handling, compositor/seat/lock behavior and platform resume remain candidates. A fast lid-open cycle alone does not prove any one is responsible.
- Sleep duration remains a confound. Some earlier fast trials were also short, and earlier delayed tests were longer. Do not promote a lid-policy change from this single result.

## Next controlled comparison

Repeat lid-open explicit suspend for a measured, comparable duration (at least a minute, followed later by a longer sleep). An attended, explicitly approved RTC wake alarm could control the actual interval without relying on estimated waiting. Keep the lid open, SPI policies `auto`, the SPI experiment removed and Touch Bar recovery unchanged. Do not automatically change lid policy, disable locking or install a broad power workaround based on the current evidence.

No additional power, driver, lid-policy or authentication settings were changed during this comparison. Both SPI controls were checked afterward as `auto`.
