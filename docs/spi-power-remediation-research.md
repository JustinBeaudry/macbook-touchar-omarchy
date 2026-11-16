# Lower-power remediations for delayed SPI input after resume

Research date: 2026-11-15. **No persistent SPI override installed; both runtime-power controls remain `auto`.** The installed Touch Bar illumination recovery is separate and unchanged.

## Recommendation

Do not ship an always-on SPI override as the default. First test a **short, post-resume-only runtime wake pulse**, restoring the original controls afterward. If that fails, test a **transition-only pre/post suspend bracket**. Both are proposed experiments, not validated fixes.

A persistent override remains a fallback only after controlled replication and measurement of the actual battery cost. We have not measured that cost and should not imply that it is either negligible or severe.

## Evidence and limits

### Local evidence

- With the PCI parent and SPI controller at `auto`, first observed fresh input after the observer resumed was 12.246 s for the keyboard and 10.622 s for the trackpad.
- With both temporarily `on`, those times were 0.003 s and 0.114 s. The user confirmed input was much better.
- The user was attempting input throughout the delay, and reported that input became usable after the screen blanked.
- **The sleep periods differed:** the systemd-sleep invocation lasted 53.568 s in the baseline and 11.032 s in the intervention. These durations include transition time, not just residency in S3. This is not a controlled repeated A/B test.
- Both parent and child were changed together, so their individual contribution is unknown.
- The timing observer measures fresh evdev activity after its own execution resumes; it is not a direct hardware-ready measurement or a complete kernel trace.
- Current settings are restored to `auto`. The controller reports `autosuspend_delay_ms=50`; its runtime state and the PCI parent's state can both become `suspended` during normal use.
- The battery was on AC and reported no discharge current during research. There is no valid battery-drain comparison yet.

See [the original comparison](spi-input-wake-delay.md).

### Matching upstream report

[Omarchy #17790](https://github.com/omacom/omarchy/issues/17790) describes the same MacBookPro14,2, Omarchy 4.5.0-3 and kernel 7.2.15-1: the screen returns from deep sleep while the SPI keyboard and trackpad remain unresponsive. It is open and, when read, had no comments or verified remediation. It corroborates the symptom; it does not establish this machine's cause.

### What Linux power controls actually mean

Linux documents `power/control=on` as preventing **runtime** power management and waking a currently runtime-suspended device. It is not a blanket instruction to forbid system suspend. The PXA SPI driver still has separate system-suspend callbacks that disable the controller/clock. Therefore our test is not evidence that forcing `on` would keep the entire controller running throughout S3.

The concern is unquantified **awake idle** consumption and possibly reduced platform low-power residency. Scope alone does not prove the cost is small: a device held active can also hold its parent active.

The platform SPI driver explicitly sets a 50 ms autosuspend delay and the SPI core uses automatic runtime PM for this controller. These facts make a runtime/system-resume interaction plausible, but do not identify the exact failing callback or prove a 50 ms timeout is the cause of a 10–12 s symptom.

Source references use upstream Linux commit `aebb7274476403040d582c61478df8f4a7bf9cd3`, not a claim that every line matches the installed Omarchy kernel:

1. [`power/control` semantics](https://github.com/torvalds/linux/blob/aebb7274476403040d582c61478df8f4a7bf9cd3/Documentation/ABI/testing/sysfs-devices-power#L35-L52).
2. [50 ms SPI autosuspend setup](https://github.com/torvalds/linux/blob/aebb7274476403040d582c61478df8f4a7bf9cd3/drivers/spi/spi-pxa2xx-platform.c#L142-L170).
3. [Automatic SPI runtime PM](https://github.com/torvalds/linux/blob/aebb7274476403040d582c61478df8f4a7bf9cd3/drivers/spi/spi-pxa2xx.c#L1295-L1310) and [separate system/runtime callbacks](https://github.com/torvalds/linux/blob/aebb7274476403040d582c61478df8f4a7bf9cd3/drivers/spi/spi-pxa2xx.c#L1482-L1535).
4. [Runtime-PM/system-sleep coordination](https://github.com/torvalds/linux/blob/aebb7274476403040d582c61478df8f4a7bf9cd3/Documentation/power/runtime_pm.rst#L455-L543), including lost firmware wake events and parent/child state dependencies.
5. [Parent dependence on active children](https://github.com/torvalds/linux/blob/aebb7274476403040d582c61478df8f4a7bf9cd3/Documentation/power/runtime_pm.rst#L372-L391).
6. [LPSS state save/restore](https://github.com/torvalds/linux/blob/aebb7274476403040d582c61478df8f4a7bf9cd3/drivers/mfd/intel-lpss.c#L471-L526) and [applespi resume initialization](https://github.com/torvalds/linux/blob/aebb7274476403040d582c61478df8f4a7bf9cd3/drivers/input/keyboard/applespi.c#L1870-L1902).

## Ranked remediation candidates

| Candidate | Rationale | Power trade-off and uncertainty |
| --- | --- | --- |
| **1. Short post-resume wake pulse** | After resume, set the validated controller(s) to `on` briefly, then restore their original values. Linux defines this write as a runtime wake request. | Preserves normal idle autosuspend outside the pulse. Untested: may be too late if the failure originates before/during system resume, or may recur immediately once `auto` is restored. |
| **2. Pre/post transition bracket** | Set `on` just before suspend, retain it for the first seconds after resume, then restore. More closely resembles the successful intervention without leaving it enabled for the entire awake session. | Could avoid a bad entry state while retaining normal idle PM afterward. Requires reliable restoration after failed/aborted suspend and no normal-session drift to `on`. Untested. |
| **3. Finite longer autosuspend delay** | Keep `control=auto`, test e.g. 500–1000 ms instead of 50 ms on the supported controller attribute. | Still permits idle suspension, but delays it after transfers. Does not necessarily repair stale state across S3; may only defer recurrence. A value of `-1` disables autosuspend and is not a battery-friendly compromise. |
| **4. Narrow persistent `on` override** | Closest to the successful test; first isolate child-only versus parent-only behavior. | Only the two-device combination has been tested, once. Keeping just the child active can still keep its parent active, so fewer writes do not guarantee lower consumption. Quantify before adopting. |
| **5. Kernel fix/regression isolation** | Trace runtime transitions and input arrival, compare an available supported alternate kernel, then supply model/device-specific evidence upstream. | Best long-term route to retaining correct PM. No released fix for this exact observation was identified in the research reviewed; source inspection alone is not a hardware-tested patch. |

These are independent of changing the screen lock or authentication stack. Neither weakening authentication nor increasing lock-screen timer delays repairs missing raw input.

## Proposed next experiment: preserve idle PM

This requires a new attended test, not automatic deployment:

1. Repeat baseline and known-good intervention at comparable sleep lengths, including at least one roughly minute-long cycle. Keep brightness, lid behavior and the input procedure consistent.
2. Test **post-resume-only** `on` for a short 1–2 s window, then restore original settings. Do not keep extending the window until a result happens.
3. Observe first input immediately, then stop input for 10–15 s and try again **after restoration to `auto`**. Verify that both devices can return to runtime-suspended state and still resume promptly on new activity.
4. If the pulse fails, test the transition bracket separately. Do not conflate the two mechanisms.
5. Once a strategy works, isolate the minimum device scope. Active-child accounting means child-only may already hold the parent awake.
6. Require repeatable input timing, physical user confirmation, unchanged lock security, no new kernel errors and verified restoration. Include a longer sleep before shipping a default.

Any implementation should be model/device-gated, save actual original values, avoid overlapping runs, have an independent restoration fail-safe, and never change global PCI/USB power policy. A process timeout alone cannot restore settings if the process is killed before cleanup; design that failure path before installing anything.

## Battery validation

Do not estimate watts from `runtime_active_time`: it measures state residency, not energy.

- Test unplugged with battery status `Discharging`, fixed display brightness, comparable radios/workload and thermal state, and no builds/updates or unrelated input diagnostics.
- Alternate baseline and candidate rather than take one sample of each. Let each settle, then collect comparable 5–10 minute idle windows; repeat.
- Where available, `voltage_now * abs(current_now) / 10^12` gives approximate battery watts for microvolt/microamp telemetry. Here `charge_now` and current telemetry exist; account for battery-gauge smoothing and measurement noise.
- Compare whole-machine discharge, not just CPU RAPL: CPU energy alone can miss peripheral or platform costs.
- Compare runtime active/suspended counters separately to verify that the candidate actually preserves idle suspension.
- Test sleep discharge independently over comparable longer sleeps; do not assume awake-idle results describe S3 drain.

## Avoid unrelated or higher-risk workarounds

- No global `pcie_aspm=off`, blanket PCI runtime-PM disable or broad USB power changes.
- No switch to `s2idle` merely to avoid this symptom without measuring sleep discharge and validating this model.
- No module unbind/reload as the first response; it can remove the only built-in input devices.
- Do not copy [Omarchy #18886](https://github.com/omacom/omarchy/pull/18886): its LPSS MMIO save/restore experiment is specifically for **MacBook8,1**, another PCI function and another failure mode. It is not evidence of safety or efficacy on MacBookPro14,2.
- Do not reinstall obsolete out-of-tree SPI DKMS as a speculative fix for an already working in-tree `applespi` driver.

## Research disposition

Recommendation: **keep both controls at `auto` now, test a short wake-only pulse next, and retain the transition bracket as the next fallback.** Do not add a default persistent SPI override to the installer on the strength of the current single comparison. No new power, driver, authentication or sleep-mode settings were changed during this research.
