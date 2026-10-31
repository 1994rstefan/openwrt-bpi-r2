# BPI-R2 GitHub-only firmware builds

This directory is the firmware source of truth for OS298. The default
`bpi-r2/25.12` branch follows reviewed upstream 25.12 release tags and explicitly
selected stable security snapshots, never upstream main or moving build inputs.
Review source/feed pins, hardware changes, resolved package deltas and CI
results together. Direct changes to the BPI branch are supported; PRs and a
second reviewer are not required for this owner-operated fork. Never force
push release history or overwrite published artifacts. Keep old branches/tags
until their consumers and recovery evidence have been inventoried.

## Build and publication

Selected candidate inputs (2026-10-31): tagged base 25.12.6 at
`64900e756efa667774214f9c6b17c113222e01f7`, reviewed `openwrt-25.12` source snapshot
`8303e9b2a004a6c3754aaa1edb32cfc7c0cfe55b`. This includes kernel 6.12.113,
CA distrust and musl regex fixes after the release; it is not an unchanged
official 25.12.6 image. `upstream.json` records both source identities, while
`feeds.conf` pins exact commits, never branch names:

| Feed | Commit | Selection |
| --- | --- | --- |
| packages | `6d7a9186ae29d7b28c38bcbea83ab839dc71b666` | Reviewed 25.12 snapshot: Unbound 1.26.2, curl 8.23.0, Chrony 4.8-r3 |
| luci | `e969939b49167516e219d465df8030d98d443d67` | Reviewed 25.12 snapshot: ACL fixes and translations |
| routing | `48c808034414a2112cf9d5261a20a320e8d0d170` | Official 25.12.6 release pin |
| telephony | `2618106d5846a4a542fdf5809f0d3ed228ce439b` | Unchanged official release pin |
| video | `094bf58da6682f895255a35a84349a79dab4bf95` | Unchanged official release pin |

The 25.12.6 target metadata/checksums were verified with the previously pinned
OpenWrt build-signing primary fingerprint
`8A8BC12F46B836C0F9CDB36F1D53D1877742E911`. Post-release source/feed snapshots
are separately reviewed upstream Git identities, not claimed as signed release
metadata. Preserve the owner-only workflow when merging upstream CI changes.

`package-floors.json` records all 190 installed packages observed read-only on
2026-10-31. Bundle construction uses the built host APK comparator to reject
removals and downgrades before publication. Update floors only from reviewed
installed state; do not lower/delete them to hide a failing candidate. This is
a static build guard, not a fresh deployment preflight or installation approval.
Keep `kmod-tls` explicitly included instead of silently dropping it. Curl 8.23
removes SMB support; OS298 uses it for HTTP(S), not SMB transfers.

Build only through `.github/workflows/bpi-r2.yml` on GitHub Actions. Dispatch on
`bpi-r2/25.12` with its exact current commit SHA, a unique request ID and either
`production` or `recovery`. Each run attempt gets a unique candidate identity.
Pushes run short input tests only; full builds are explicit manual dispatches.
There are no automatic PR builds or review gates for this single-device fork.
Candidate publication creates a prerelease, not deployment approval.
Never create upstream PRs or push changes to `openwrt/openwrt` without a new
explicit owner request; upstream is a read-only source for this project.

The pinned container base and feed commits plus recorded toolchain/environment
metadata support traceability; bit-for-bit reproducibility is not claimed. The
complete candidate tarball contains images, manifest/config, package outputs,
FIT listing, logs and provenance. GitHub attests the tarball in a separate job
that never executes the source/build scripts. Verify the expected repository,
workflow, source commit, run and artifact digest when importing. Keep independent
verified copies; GitHub releases and expiring workflow artifacts are not backups.

There is deliberately no automatic production promotion. Select the verified
candidate bytes/hash in the infrastructure repository's approved deployment
manifest. If a stable release is later desired, promote those same bytes without
rebuilding, and require a separate reviewed publication operation.

## Profiles and safety

Both profiles use the same source, feeds and package selection. Production adds
only `/etc/os298-firmware.json`; it does not embed SSH authorization, custom
DNSSEC bootstrap overrides or recovery network defaults. Unbound itself ships
`/etc/unbound/root.key`: production must match that exact pinned-feed default,
never the custom recovery seed. The selected feed includes the KSK-2024 anchor,
but an immutable package seed is not the mutable RFC 5011 state. Production requires an existing managed
installation, an audited backup that restores valid mutable DNSSEC state, and
post-upgrade DNSSEC verification; otherwise deployment must block. Its SD output is not
an OS298 recovery bootstrap image. Recovery adds the public OS298 SSH key,
public DNSSEC bootstrap anchor and initial LAN4 defaults; it is for explicitly
authorized provisioning only, never ordinary settings-preserving updates.
Recovery provenance includes the built authorization file's SHA-256; OS298 import
requires it to match the canonical control-node public key. Key rotation must
update both projects explicitly. Recovery build/import and hardware acceptance
remain separate from a successful production candidate.

The BPI kernel includes the optional DS3231 overlay and upstream WRRD fix. The
redundant local WRRD backport is removed for the selected kernel, and CI checks
the compiled I2C source for the corrected WRRD condition. The production
FIT must support the actual persistent selector. Kernel ABI is recorded rather
than assumed equal to official images; only matching modules may be installed.
Automatic userspace migration of boot commands has been removed: inspecting or
changing U-Boot environment/bootloader is a separate authorized operation. New
media retain the bootloader's built-in selectors; existing installations must
already have a compatible reviewed boot environment.

The CI has no router access. OS298 Ansible owns exact-artifact import, encrypted
protection, `sysupgrade -T`, one authorized installation and functional verification.
No successful build, prerelease or timeout authorizes flashing/rebooting a device.

## Checks

`python3 -m unittest discover -s bpi-r2/tests -v` tests the source contract without
compiling firmware. Full build/artifact checks run in CI. Fresh recovery and
retained-configuration first boot still require separate hardware acceptance.
