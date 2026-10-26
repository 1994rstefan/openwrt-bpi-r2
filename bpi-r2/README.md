# BPI-R2 GitHub-only firmware builds

This directory is the firmware source of truth for OS298. The default
`bpi-r2/25.12` branch follows reviewed upstream 25.12 release tags, not upstream
main. Merge updates through short-lived branches and review source/feed pins,
hardware changes, resolved package deltas and CI results together. Never force
push release history or overwrite published artifacts. Keep old branches/tags
until their consumers and recovery evidence have been inventoried.

## Build and publication

Build only through `.github/workflows/bpi-r2.yml` on GitHub Actions. Dispatch on
`bpi-r2/25.12` with its exact current commit SHA, a unique request ID and either
`production` or `recovery`. Each run attempt gets a unique candidate identity.
PR builds cannot publish; pushes validate inputs but do not publish firmware.
Candidate publication creates a prerelease, not deployment approval.

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
never the custom recovery seed. This legacy vendor default is not proof of a
usable post-rollover trust anchor. Production requires an existing managed
installation, an audited backup that restores valid mutable DNSSEC state, and
post-upgrade DNSSEC verification; otherwise deployment must block. Its SD output is not
an OS298 recovery bootstrap image. Recovery adds the public OS298 SSH key,
public DNSSEC bootstrap anchor and initial LAN4 defaults; it is for explicitly
authorized provisioning only, never ordinary settings-preserving updates.

The BPI kernel includes the optional DS3231 overlay and WRRD fix. The production
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
