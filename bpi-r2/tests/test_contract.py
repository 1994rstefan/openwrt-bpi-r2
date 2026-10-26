"""Offline tests of the firmware contract, without compiling firmware locally."""

import importlib.util
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("check_config", ROOT / "bpi-r2/check-config.py")
config = importlib.util.module_from_spec(spec)
spec.loader.exec_module(config)


class ContractTests(unittest.TestCase):
    def test_config_cannot_silently_drop_packages_or_negative_settings(self):
        seed = 'CONFIG_PACKAGE_luci-ssl=y\n# CONFIG_KERNEL_KALLSYMS is not set\n'
        config.check(seed, seed + 'CONFIG_OTHER=y\n')
        for resolved in ('CONFIG_PACKAGE_luci-ssl=y\n', '# CONFIG_KERNEL_KALLSYMS is not set\n'):
            with self.assertRaises(ValueError):
                config.check(seed, resolved)

    def test_feeds_are_exact_commits(self):
        lines = (ROOT / "bpi-r2/feeds.conf").read_text().splitlines()
        self.assertEqual(len(lines), 5)
        for line in lines:
            self.assertRegex(line, r'^src-git [a-z]+ https://[^ ]+\^[0-9a-f]{40}$')

    def test_container_and_actions_are_digest_pinned(self):
        container = (ROOT / "bpi-r2/Containerfile").read_text()
        self.assertRegex(container, r'FROM debian:bookworm-slim@sha256:[0-9a-f]{64}')
        workflow = (ROOT / ".github/workflows/bpi-r2.yml").read_text()
        for reference in re.findall(r'uses: ([^\s]+)', workflow):
            self.assertRegex(reference, r'@[0-9a-f]{40}$')
        self.assertNotIn('--clobber', workflow)
        self.assertNotIn('pull_request_target', workflow)

    def test_no_automatic_boot_environment_migration(self):
        self.assertFalse((ROOT / 'target/linux/mediatek/mt7623/base-files/etc/uci-defaults/31_bpi-r2-fit-selectors').exists())

    def test_production_has_no_recovery_or_private_credentials(self):
        self.assertFalse((ROOT / 'bpi-r2/files/production').exists())
        for path in (ROOT / 'bpi-r2/files').rglob('*'):
            if path.is_file():
                self.assertNotRegex(path.read_text(), r'-----BEGIN (?:\w+ )*PRIVATE KEY-----')
        build = (ROOT / 'bpi-r2/build.sh').read_text()
        self.assertIn('if [ "$profile" = recovery ]; then', build)

    def test_rtc_and_network_packages_are_explicit(self):
        packages = (ROOT / 'bpi-r2/required-packages.txt').read_text().splitlines()
        for name in ('kmod-rtc-ds1307', 'kmod-bonding', 'kmod-wireguard', 'chrony-nts', 'unbound-daemon'):
            self.assertIn(name, packages)
