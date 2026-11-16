# USB comparison: perceived freeze is not confined to built-in SPI input

## User observation — 2026-11-15

A wired DasKeyboard was connected for comparison, without changing installed recovery behavior. The user reported the first wake was completely unresponsive **even with the USB keyboard**. They closed the lid again; the next wake worked.

The timing-only observer monitored both DasKeyboard event nodes and the built-in SPI keyboard/trackpad without input grabs or recording key codes, text, passwords or coordinates.

## First wake

Relative to the observer resuming at `21:27:50.762`:

- Fresh built-in keyboard activity: **2.901 s**.
- Fresh built-in trackpad activity: **3.436 s**.
- Fresh DasKeyboard activity: **6.479 s**.

The user's report of an unresponsive UI despite activity reaching evdev is not explained by a failure confined to the built-in SPI input devices. It does not rule out all hardware/firmware faults or establish a particular compositor bug.

Touch Bar recovery and the optional SPI pulse both ran; the pulse restored original policies to `auto`. These successful command/cleanup results did not establish successful UI interaction.

## Lid-event/re-suspend confound

Logind recorded:

```text
21:27:49.898699 Lid opened
21:27:49.902555 Lid closed
21:27:51.110010 First suspend operation finished
21:27:51.116547 Suspending again
21:27:51.767198 Lid opened
```

The approximately 4 ms open/closed transition is a lid-state/event lead, not proof that the physical sensor is defective. A second suspend was already queued immediately after the first completed. Repeated sleep-inhibitor refusals/restarts occurred during this in-flight transition. They could be a symptom rather than the cause of the perceived freeze.

Successful authentication/unlock was logged around `21:28:01.627`, immediately before the next actual suspend began. This does not cleanly match a simple interpretation that all input was absent until the second wake; event arrival, perceived UI response and queued suspend operations must remain distinct evidence.

Earlier delayed single-cycle tests did not all show an immediate lid re-close. The lid sequence therefore does not establish a complete explanation for every reported delay.

## Second wake and USB availability

The observer saw the second resume at `21:28:20.487`, reopened/retired both old DasKeyboard descriptors and reported no matching USB nodes available in the captured interval. Built-in input activity subsequently arrived and the user reported recovery. Do not describe this as a successful USB-input validation on the second cycle or infer why the USB device disappeared without investigating its connection/controller path.

## Disposition and next comparison

- The SPI power workaround has not demonstrated a reliable end-to-end benefit and should not be broadened or made always-on.
- Both SPI controls were checked afterward as `auto`. The optional wake-only feature remains installed pending user-authorized removal; confirmed Touch Bar illumination recovery is independent.
- Recommend removing the unproven optional SPI feature and testing **one menu-triggered suspend with the lid left open throughout**, USB keyboard connected. Do not combine menu suspend with lid close.
- That comparison separates lid-event behavior from the shared Linux/firmware/compositor/lock resume path. It is not a test of disabling the lock or authentication.

Related upstream evidence: [matching-model input-delay report #17790](https://github.com/omacom/omarchy/issues/17790), [sleep-inhibitor race #15270](https://github.com/omacom/omarchy/issues/15270), and proposed, unmerged monitor fixes [#13782](https://github.com/omacom/omarchy/pull/13782) / [#10455](https://github.com/omacom/omarchy/pull/10455). Those reports do not prove this machine's root cause. No upstream patch was installed during this comparison.

Evidence: bounded system/user journals, timing-only input trace and explicit user feedback. Full journals, identifiers and input content are not published.
