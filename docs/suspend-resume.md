# Suspend/resume investigation

## 2026-11-15 — open incident

**Reported:** Touch Bar stopped working and behaves oddly around sleep.

**Observed before recovery:**

- System `t1-touchbar-hw.service` and user `t1-touchbar.service` were both active, with processes dating from before the sleep cycles.
- `/dev/dri/touchbar` existed and pointed to `card0`; `/run/t1bridge/touchbar.sock` existed.
- The system journal recorded completed suspend/resume cycles.
- Kernel messages included a T1 configuration-selector USB reset at resume. Thunderbolt/PCIe power-management warnings also appeared around sleep. Neither observation independently establishes the Touch Bar root cause.
- The renderer journal contained older `selected renderer unavailable; using built-in` and `configured desktop provider is unavailable` messages. These do not prove the cause of the current panel failure.
- The previous keyboard-brightness provider override was still configured.

## Recovery attempted

```bash
systemctl --user restart t1-touchbar.service
```

The restart completed and a new renderer process was active. No new error appeared in the immediate renderer journal. **The user subsequently confirmed the panel was still blank: renderer-only restart did not recover this incident.**

### Second recovery attempt

Restarted the system hardware service with graphical privilege authorization, then restarted the user renderer:

```bash
pkexec /usr/bin/systemctl restart t1-touchbar-hw.service
systemctl --user restart t1-touchbar.service
```

Both services returned to active with new processes. The old renderer logged a lost hardware connection during the hardware-service restart, as expected. The user confirmed the Touch Bar remained blank after this second attempt. **Restarting both services did not restore the display.**

No module reload, manual USB reset, firmware operation or automatic resume hook was performed.

## Recovery ladder

1. Capture the bounded state below before changing anything.
2. Restart only the user renderer and physically test the panel, touch input, brightness and volume.
3. If that does not recover it, inspect fresh renderer/hardware and kernel logs. Consider a hardware-service restart only as a separate authorized test; do not assume renderer recovery requires it.
4. Reproduce a sleep/wake cycle only when the user is ready; it interrupts the desktop.
5. If renderer-only restart consistently restores operation, evaluate a user-session resume listener. Do not install an automatic restart on the strength of one unconfirmed attempt.
6. Escalate to driver/device investigation only with evidence. Avoid firmware recovery as a routine resume fix.

## Bounded diagnostics

```bash
systemctl --user status t1-touchbar.service --no-pager
systemctl status t1-touchbar-hw.service --no-pager
journalctl --user -b -u t1-touchbar.service --no-pager -n 60
journalctl -b -u t1-touchbar-hw.service -u systemd-suspend.service --no-pager -n 80
ls -l /dev/dri/touchbar /run/t1bridge/touchbar.sock
```

Inspect kernel logs in a narrow window around the affected resume. Review output locally before sharing; status/journal output can expose personal identifiers.

## Next evidence needed

- Was the screen black, frozen, or displaying controls with no touch response?
- Neither renderer-only restart nor hardware-service + renderer restart restored the display. Investigate device/driver display state next rather than installing a service-restart resume hook.
- Does the issue recur on the next sleep/wake, and does the same recovery work?
- Does the hardware service log any new errors during the failure?

Evidence: direct read-only system/service/device checks and bounded journals from the affected machine on 2026-11-15, followed by the renderer-only restart. Public notes intentionally omit raw journals and machine identifiers.
