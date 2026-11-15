# Confirmed post-sleep recovery — 2026-11-15

## Outcome

**User confirmed: “touchbar is back!”** after one attended wake sequence on MacBookPro14,2, Omarchy 4.5.0-3, kernel 7.2.15-1-omarchy, T1Bridge 0.1.12-1.

The successful sequence was:

1. Evaluate the verified ACPI method `\_SB.PCI0.XHC1.RHUB.ASOC.SOCW` with argument `1` (host awake).
2. Send the T1 display interface its 15-byte HID feature report 3 awake value: `03 02 f4 01` followed by eleven zero bytes.

Observed output:

```text
Display awake byte before: 0x01
SOCW(1) result: 0x0
Sent one 15-byte display-awake report.
Display awake byte after: 0x02
```

The user then physically confirmed illumination. A successful return code or HID readback alone would not establish that.

## Verification before the call

- The user explicitly approved one attempt after being warned that ACPI calls can freeze affected machines and asked to save work.
- The machine's `APP7777:00` ACPI device path was `\_SB_.PCI0.XHC1.RHUB.ASOC`.
- Its own SSDT6 was read and decompiled locally using `iasl`, extracted from an Arch package whose detached signature was verified. No package installation was required.
- SSDT6 contained a one-argument serialized `SOCW` method under that device. The awake branch sends mailbox messages 6 then 2; it does not invoke the separate `FRST` method.
- The recovery helper checked the model and device path, and compared the live SSDT6 hash with the table inspected immediately beforehand.
- Exactly one display HID node matched USB vendor `05ac`, product `8600`, interface `06`.

## Scope and safety

This was **one manual recovery in an existing post-S3 dark state**, not repeated-cycle validation or a durable installed resume fix. The report-awake write alone was not tested independently in this incident. The successful combined sequence does not isolate each step's necessity on this machine.

No `SOCW(0)`, `FRST`, whole-device USB reset, firmware flashing, keybag modification or biometric operation was performed by the successful recovery helper. No automatic sleep hook was installed.

Do not copy this ACPI path to another machine without verifying its firmware and obtaining approval for the risk. Do not use `FRST`: upstream reports it can leave the T1 in recovery. Do not experiment with a sleep/awake pair on an awake host.

## Earlier unsuccessful attempts

- Restart the user renderer: panel remained blank.
- Restart the hardware service and renderer: panel remained blank.
- Rebind only the USB display interface and restart services: panel remained blank.

The repeated “selected renderer unavailable” notification was a separate misleading fallback message when no custom renderer was configured. Its local messaging workaround did not recover the panel.

## Next step

If authorized, implement a narrowly gated resume workaround with bounded execution and logging, then validate an attended sleep/wake cycle. Keep manual recovery, automatic-hook installation, and repeated reliability testing as separate milestones.

## Provenance

Direct local firmware inspection and the one-shot helper's bounded output, followed by explicit user confirmation on 2026-11-15. Firmware tables and full logs are intentionally not published.

The recovery direction came from later reports in [T1Bridge issue #18](https://github.com/standardagents/t1bridge/issues/18), including a matching MacBookPro14,2/package/kernel report. Local confirmation, rather than those external reports alone, establishes the outcome here.
