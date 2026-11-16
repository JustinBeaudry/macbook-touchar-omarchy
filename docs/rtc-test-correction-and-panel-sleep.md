# RTC test correction and Touch Bar remaining lit

## User feedback — 2026-11-15

The user reported that the wake was instantly responsive, no longer wanted the external-keyboard comparison for now, and observed that the Touch Bar did not appear to go to sleep. Keyboard comparison testing was stopped rather than expanded.

## Invalid timed-test implementation

The intended controlled test armed an RTC alarm for 60 seconds, then invoked normal `systemctl suspend` so standard locking and Touch Bar recovery would run. The temporary controller incorrectly assumed that the command returned only after resume.

Actual trace:

```text
22:08:20.026 RTC alarm armed for 22:09:20
22:08:20.029 logind received suspend request
22:08:20.033 controller saw systemctl return and cleared its alarm
22:08:21.132 systemd-sleep began suspend operation
22:08:32.058 systemd-sleep returned
```

**The controller cleared its own alarm before sleep began. This is not valid 60-second controlled evidence.** The systemd-sleep invocation lasted approximately 10.926 s including transitions. The actual cause of the early wake was not established.

The user's report of instant responsiveness remains valid qualitative feedback for this short cycle. It must not be presented as validation of a minute-long lid-open suspend or proof that duration is irrelevant. No fresh post-resume input was recorded in the observation window; no device-ready latency should be invented from that trace.

The error was acknowledged to the user. The temporary controller was corrected to distinguish request acceptance from completion: wait for logind's sleep transition and a suspend clock gap before cleaning up the alarm, and explicitly flag a wake while its alarm is still pending. **That corrected controller has not been rerun or validated.** No more keyboard/RTC test was initiated after the user asked to stop that comparison.

At inspection the RTC alarm was empty, both SPI policies remained `auto`, the experimental SPI option remained removed, and the confirmed Touch Bar wake recovery was still installed.

## Touch Bar sleep observation

Kernel logs show a `deep`/S3 suspend entry and exit for this attempt, despite the visible Touch Bar observation. That is not a measurement of panel power, exact S3 residency or sleep energy use.

Installed T1Bridge 0.1.12's `appletbdrm_t1_park()` clears the display and sends the 15-byte HID feature report 3 park value beginning `03 01 f4 01` to interface 6. It does not send the ACPI host-sleep mailbox notification. The existing local recovery sends only the verified `SOCW(1)` host-awake call after system resume and the display-awake report when needed.

[Upstream PR #58](https://github.com/standardagents/t1bridge/pull/58), still open and unmerged when read, reports that the park operation can leave the panel powered/refreshing. It proposes paired `SOCW(0)`/`SOCW(1)` from system PM notifications, without calling those methods at probe. Its reported physical test was on **MacBookPro14,3 with s2idle**, not this **MacBookPro14,2 with deep/S3**. Its author explicitly lists S3 and other models as untested, and reports that calling the sleep/awake pair on an awake host left the display dark until full power-off.

Thus the observation is consistent with an existing display-power lifecycle limitation, not proof that the PR fixes this machine. No pre-sleep ACPI call, kernel patch or extra hook was installed in response. The currently confirmed wake workaround must not be described as complete Touch Bar suspend/power support.

## Disposition

- Keep the removed SPI workaround removed; do not trade normal idle power-saving for an unproven benefit.
- Do not count this attempt as the promised controlled 60-second test.
- Do not infer measured battery drain or absence of sleep from the panel's appearance alone.
- Review a properly gated upstream display-power lifecycle fix before considering a separate attended test, including aborted-suspend handling and recovery access. Do not replay `SOCW(0)` on a healthy awake machine as a casual test.
- User's external-keyboard testing is paused. No additional test or system change is authorized merely by this note.

Evidence: reviewed temporary controller output, bounded system/kernel journals, installed driver source, explicit user feedback and upstream PR #58. No credentials, input content, firmware tables or raw journals are published.
