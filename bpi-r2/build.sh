#!/bin/bash
# CI-only build entrypoint. It never accesses infrastructure or secrets.
set -euo pipefail
test "${GITHUB_ACTIONS:-}" = true
profile=${PROFILE:?}
case "$profile" in production|recovery) ;; *) exit 1 ;; esac
test "$(git rev-parse HEAD)" = "$EXPECTED_SHA"
test -z "$(git status --porcelain --untracked-files=no)"
test ! -e files
test ! -e bin
test ! -e feeds.conf
cp bpi-r2/feeds.conf feeds.conf
./scripts/feeds update -a
./scripts/feeds install -a
mkdir -p files/etc
if [ "$profile" = recovery ]; then
    cp -a bpi-r2/files/recovery/. files/
    chmod 0755 files/etc/uci-defaults/99-os298-recovery
    chmod 0600 files/etc/dropbear/authorized_keys
fi
python3 bpi-r2/metadata.py identity
cp bpi-r2/config.seed .config
release=$(python3 bpi-r2/metadata.py release)
version="${release}-os298-${profile}-${GITHUB_RUN_ID}.${GITHUB_RUN_ATTEMPT}"
printf 'CONFIG_VERSION_NUMBER="%s"\nCONFIG_VERSION_CODE="r%s"\n' "$version" "${EXPECTED_SHA:0:12}" >> .config
printf 'CONFIG_VERSION_REPO="https://downloads.openwrt.org/releases/%s"\n' "$release" >> .config
make defconfig
python3 bpi-r2/check-config.py bpi-r2/config.seed .config
make -j"${JOBS:-4}" download
make -j"${JOBS:-4}" BUILD_LOG=1
python3 bpi-r2/metadata.py bundle
