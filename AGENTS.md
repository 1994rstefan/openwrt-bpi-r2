# Owner-operated BPI-R2 fork

- This fork exists only for the owner's BPI-R2. Communicate with the owner in
  German; keep source, comments and documentation in English.
- Upstream `openwrt/openwrt` is READ-ONLY. Never open upstream pull requests or
  push upstream changes without a new explicit owner request. Fetching reviewed
  upstream releases and merging them into this fork is allowed.
- Default integration branch: `bpi-r2/25.12`. Direct commits are the intended
  single-maintainer workflow. Do not require pull requests, a second reviewer
  or automatic full PR builds. Preserve existing history and recovery releases.
- Firmware inputs and checks live under `bpi-r2/`. Build firmware only with
  `.github/workflows/bpi-r2.yml` on GitHub Actions, never on the local machine.
  Pushes run short checks; full builds require explicit dispatch with exact SHA,
  request ID and production/recovery profile. Local offline unit tests are fine.
- Production must not include custom recovery network/authorization overrides.
  Unbound's root.key must match the pinned feed. Its legacy package seed does
  not prove valid runtime DNSSEC state; deployment must preserve the live key
  and verify DNSSEC. Recovery files are for separately authorized provisioning.
- Keep exact source/feed/container identities, package/FIT/ABI checks and
  authenticated candidate provenance. Do not disable gates to publish a build,
  overwrite release assets or treat adjacent checksums as authentication.
- A CI candidate/prerelease is not installation approval. CI has no router
  credentials or access. OS298 Ansible owns encrypted protection, actual upgrade
  path/package-delta approval, installation and live functional verification.
- Do not write firmware, U-Boot environment/bootloader, reboot the router or
  replace recovery media without exact target and maintenance-window approval.
- Before changes run `python3 -m unittest discover -s bpi-r2/tests -v` and shell
  syntax checks. Hardware acceptance and real attestation/import evidence must
  be reported separately from source tests or a successful compile.
