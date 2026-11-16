# Review of upstream SOCW sleep-power candidate

Reviewed 2026-11-15. **Source review and isolated tests/builds only. No candidate driver loaded, package installed, firmware method called, or active sleep configuration changed.**

## Exact candidate

- [T1Bridge PR #58](https://github.com/standardagents/t1bridge/pull/58), open/unmerged when reviewed.
- Head: `bd58a71875408592c124d3385922d84a48ac1484` (`makoni/t1bridge`, `socw-sleep`).
- Base: `81cbdf81026a16e02f0bea74735c6b029a8ffae2` (the v0.1.12 source).
- `gh pr checks` reported no checks for this head. Do not interpret the PR's mergeability or local compilation as CI/release approval.

## Bottom line

**Promising mechanism, not ready to install as-is.** It addresses the missing host-sleep notification rather than merely hiding the Touch Bar's output. The synthetic tests and direct module build pass, but the DKMS staging recipe omits a required new header, aborted-suspend behavior has a known physical risk, and the handoff from our current wake helper is not validated.

## Reproduced deployment blocker: required header omitted

The new [driver include](https://github.com/standardagents/t1bridge/blob/bd58a71875408592c124d3385922d84a48ac1484/kernel/appletbdrm-t1/appletbdrm.c#L91-L95) requires `appletbdrm_socw.h`, but the [DKMS package file list](https://github.com/standardagents/t1bridge/blob/bd58a71875408592c124d3385922d84a48ac1484/packaging/arch/t1bridge-dkms/PKGBUILD#L25-L28) copies only the old source/header set.

Reproduction was isolated and unprivileged:

1. Use the candidate checkout as the package recipe's source tree.
2. Run only its inspected `package()` function with source/package directories under a temporary directory. No host package manager or scriptlet runs.
3. Build the display module from the resulting staged `/usr/src` tree against the installed kernel headers.

Result:

```text
fatal error: appletbdrm_socw.h: No such file or directory
```

Copying **only that missing header into the temporary staged tree** made the same display-module build pass. This establishes the staging omission, not a full DKMS/release lifecycle test. It does not mean the currently installed official 0.1.12 package is broken: that release does not contain this PR's include. A candidate/release assembled with the new code must fix the file list and follow the project's version/archive preparation process.

## Safety and integration findings

### 1. Aborted suspend remains a physical recovery risk

The notifier sends `SOCW(0)` from `PM_SUSPEND_PREPARE`, remembers the attempt even on error, and sends `SOCW(1)` from `PM_POST_SUSPEND` when it owes an answer. `PM_POST_SUSPEND` also follows an aborted/failed suspend.

The candidate itself documents that a sleep/awake pair on an awake host **without actual sleep** left the author's panel dark until full power-off. The synthetic tests prove that the compensating wake call is issued and software state is cleared; they do **not** prove that an aborted suspend physically recovers the panel. This needs an explicit recovery plan, not a claim that the `POST` handler makes failure safe.

References: [notifier and abort handling](https://github.com/standardagents/t1bridge/blob/bd58a71875408592c124d3385922d84a48ac1484/kernel/appletbdrm-t1/appletbdrm_socw.h#L189-L247), [documented awake-host risk](https://github.com/standardagents/t1bridge/blob/bd58a71875408592c124d3385922d84a48ac1484/kernel/appletbdrm-t1/README.md#L50-L63).

### 2. Do not stack it with our existing ACPI wake helper

The installed `90-macbook-touchbar-wake.conf` runs the local helper after systemd-sleep returns. That helper sends `SOCW(1)` and, if needed, the HID display-awake report. The candidate driver would already have sent its own `SOCW(1)` in the kernel PM notifier. Leaving both enabled would duplicate wake calls; composition is untested.

Removing our helper without a replacement contract is also premature. The PR skips the park report only after an acknowledged `SOCW(0)`. On a failed/unacknowledged sleep write it falls back to the old park behavior. Its unchanged USB rearm does not explicitly send the HID awake report. Our current helper independently covers that awake-byte step. A test plan must separate ownership of the ACPI call from any remaining HID fallback, rather than delete or stack helpers blindly.

References: [park decision](https://github.com/standardagents/t1bridge/blob/bd58a71875408592c124d3385922d84a48ac1484/kernel/appletbdrm-t1/appletbdrm_socw.h#L256-L275), [unchanged rearm](https://github.com/standardagents/t1bridge/blob/bd58a71875408592c124d3385922d84a48ac1484/kernel/appletbdrm-t1/appletbdrm_resume.h#L9-L59).

### 3. S3 ordering and blocking ACPI calls need hardware validation

The sleep call runs before device suspend callbacks; the wake call runs at the PM post-suspend notification, after device resume callbacks. Thus USB/DRM resume can run before the host-awake mailbox write. The code compiles and the s2idle test passed, but that does not establish behavior on this model's deep/S3 path with its observed T1 USB descriptor/reset errors. This is an ordering/performance validation gap, not a reproduced deadlock.

ACPICA evaluation is blocking and is not bounded by a driver-enforced deadline. A userspace `timeout` around a suspend request cannot guarantee recovery from a method stuck inside the kernel. No live ACPI call was made during this review.

### 4. Broad automatic T1 behavior, narrow physical evidence

Method discovery is limited to T1 hardware and a unique one-argument `SOCW` below the USB host controller's first ACPI ancestor, with a depth bound. Nothing is evaluated during probe. The code holds a module reference through an answered sleep and retains module-level state across device re-enumeration, rather than relying only on the old USB interface surviving.

Those are sensible boundaries. They are not a DMI/firmware opt-in, a guarantee against all firmware behavior, or proof that every T1 model is supported. The compiled synthetic harness does not cover real contention, firmware namespace depth enforcement, every ACPICA allocation/discovery failure, or actual module-unload races.

Reference: [candidate discovery and state code](https://github.com/standardagents/t1bridge/blob/bd58a71875408592c124d3385922d84a48ac1484/kernel/appletbdrm-t1/appletbdrm_socw.h#L28-L164), [declared harness limits](https://github.com/standardagents/t1bridge/blob/bd58a71875408592c124d3385922d84a48ac1484/kernel/appletbdrm-t1/test_appletbdrm_socw.c#L1-L20).

## Evidence by strength

### Locally reproduced, no live hardware changes

- `make -C kernel/appletbdrm-t1 test sanitize`: SOCW, resume-fault and protocol harnesses all passed, including AddressSanitizer/UndefinedBehaviorSanitizer runs.
- Direct display-module build with `W=1` against `7.2.15-1-omarchy` headers passed without warnings in the observed output.
- Current-recipe staged display-module build failed for the missing header; copying that header into the isolated stage made it pass.
- Full `make quality`, all-module DKMS lifecycle, installation/removal, and physical candidate suspend were **not** run. The active module/package paths remained the installed stock versions; only temporary `.ko` build artifacts were produced.

### Upstream physical reports, not our validation

- The PR author's kernel-branch evidence is MacBookPro14,3, Linux 7.2.15, **s2idle**, approximately 20 seconds: panel dark during sleep and lit afterward. It is not this model or S3.
- A later [MacBookPro14,2 userspace-hook report](https://github.com/standardagents/t1bridge/pull/58#issuecomment-6663991071) matches stock T1Bridge 0.1.12-1, Omarchy 4.5.0-3 and kernel 7.2.15-1-omarchy. One deep/S3 cycle logged both method calls returning `0x0`; the strip was initially dark after lid-open and lit by session unlock. Input briefly froze. **That branch was not installed, Touch ID was not tested, and panel power-off during sleep was not established by that report.**
- The [userspace hook discussion](https://github.com/omacom/omarchy/pull/11570#issuecomment-6612732284) explicitly warns not to call the pair on an awake host and notes the same concern for an aborted suspend. Do not install its script automatically from the discussion.

## Recommendation before any candidate installation

1. Prepare the packaging-header fix and a reproducible staged package test; do not hand-copy an untracked module into the live kernel search path.
2. Keep the candidate pinned, distinguish it from stock package versions, and retain a verified rollback to the current package/module and wake helper.
3. Resolve duplicate ACPI ownership and HID-fallback behavior before enabling the candidate; do not run kernel and userspace sleep/awake pairs together.
4. Obtain separate approval for a hardware test, including the acknowledged aborted-suspend/full-power-off risk and recovery access. A compensating call alone is not proof of a safe rollback.
5. Use the same controlled lid-open/RTC setup for baseline and candidate, with explicit temporary lid-wake isolation if authorized, so spurious early wake does not confound panel observation. Check input, camera/network and password fallback separately; do not assume Touch ID survives.
6. Observe the panel physically throughout sleep and record the actual sleep interval. Only then discuss repeated validation or energy measurement.

No upstream comment, PR, package publication, driver installation or firmware operation was performed as part of this review. Current lid wake remains enabled, the RTC alarm is empty, SPI runtime PM remains normal, and the existing confirmed wake recovery is unchanged.
