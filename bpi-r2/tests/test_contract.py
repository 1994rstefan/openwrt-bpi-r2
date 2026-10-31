"""Offline tests of the firmware contract, without compiling firmware locally."""

import importlib.util
from pathlib import Path
import re
import tempfile
import json
import hashlib
import unittest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("check_config", ROOT / "bpi-r2/check-config.py")
config = importlib.util.module_from_spec(spec)
spec.loader.exec_module(config)
metadata_spec = importlib.util.spec_from_file_location("metadata", ROOT / "bpi-r2/metadata.py")
metadata = importlib.util.module_from_spec(metadata_spec)
metadata_spec.loader.exec_module(metadata)


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

    def test_upstream_baseline_is_an_exact_reviewed_release_commit(self):
        baseline = json.loads((ROOT / 'bpi-r2/upstream.json').read_text())
        self.assertEqual(baseline['release'], '25.12.6')
        self.assertEqual(baseline['commit'], '64900e756efa667774214f9c6b17c113222e01f7')
        self.assertEqual(baseline['source_commit'], '8303e9b2a004a6c3754aaa1edb32cfc7c0cfe55b')
        self.assertEqual(baseline['source_branch'], 'openwrt-25.12')

    def test_container_and_actions_are_digest_pinned(self):
        container = (ROOT / "bpi-r2/Containerfile").read_text()
        self.assertRegex(container, r'FROM debian:bookworm-slim@sha256:[0-9a-f]{64}')
        workflow = (ROOT / ".github/workflows/bpi-r2.yml").read_text()
        for reference in re.findall(r'uses: ([^\s]+)', workflow):
            self.assertRegex(reference, r'@[0-9a-f]{40}$')
        self.assertNotIn('--clobber', workflow)
        self.assertNotIn('pull_request_target', workflow)

    def test_owner_fork_builds_are_explicit_not_push_or_pr_triggered(self):
        workflow = (ROOT / '.github/workflows/bpi-r2.yml').read_text()
        self.assertNotIn('pull_request:', workflow)
        self.assertNotIn("github.event_name == 'pull_request'", workflow)
        self.assertIn("if: github.event_name == 'workflow_dispatch'", workflow)
        self.assertEqual([path.name for path in (ROOT / '.github/workflows').glob('*.yml')], ['bpi-r2.yml'])

    def test_recovery_authorization_is_the_reviewed_public_key(self):
        key = (ROOT / 'bpi-r2/files/recovery/etc/dropbear/authorized_keys').read_bytes()
        self.assertEqual(hashlib.sha256(key).hexdigest(),
                         '039ca07f5ced98e7ba40f91ff259c3a97d9f6b1c7c733a76107f043efc5e3a18')

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
        for name in ('kmod-rtc-ds1307', 'kmod-bonding', 'kmod-tls', 'kmod-wireguard', 'chrony-nts', 'unbound-daemon'):
            self.assertIn(name, packages)

    def test_future_images_do_not_include_unneeded_sftp_server(self):
        negative = '# CONFIG_PACKAGE_openssh-sftp-server is not set'
        self.assertIn(negative, (ROOT / 'bpi-r2/config.seed').read_text().splitlines())
        self.assertNotIn('openssh-sftp-server', (ROOT / 'bpi-r2/required-packages.txt').read_text().splitlines())
        floors = json.loads((ROOT / 'bpi-r2/package-floors.json').read_text())
        self.assertNotIn('openssh-sftp-server', floors['packages'])
        config.check(negative, negative)
        with self.assertRaises(ValueError):
            config.check(negative, 'CONFIG_PACKAGE_openssh-sftp-server=y')

    def test_release_and_repository_urls_follow_the_selected_baseline(self):
        build = (ROOT / 'bpi-r2/build.sh').read_text()
        self.assertIn('release=$(python3 bpi-r2/metadata.py release)', build)
        self.assertIn('"${release}-os298-', build)
        self.assertNotIn('25.12.5', build)

    def test_wrrd_fix_is_checked_in_kernel_source_not_duplicated(self):
        marker = '/* checking if we can skip restart and optimize using WRRD mode */\n'
        metadata.check_wrrd(marker + 'if (num == 2) {')
        for text in ('unrelated source', marker + 'if (i2c->auto_restart && num == 2) {'):
            with self.assertRaises(ValueError):
                metadata.check_wrrd(text)
        self.assertFalse((ROOT / 'target/linux/mediatek/patches-6.12/950-i2c-mt65xx-fix-wrrd-without-auto-restart.patch').exists())

    def test_package_floors_fail_closed_for_removal_downgrade_or_invalid_comparison(self):
        metadata.check_package_floors({'curl': 'new'}, {'curl': 'old'}, lambda new, old: '>')
        metadata.check_package_floors({'curl': 'same'}, {'curl': 'same'}, lambda new, old: '=')
        for comparison in ('<', '', 'unrecognized'):
            with self.assertRaises(ValueError):
                metadata.check_package_floors({'curl': 'older'}, {'curl': 'installed'}, lambda new, old: comparison)
        with self.assertRaises(ValueError):
            metadata.check_package_floors({}, {'curl': 'installed'}, lambda new, old: '>')
        with self.assertRaises(ValueError):
            metadata.check_package_floors({'curl': 'candidate'}, {}, lambda new, old: '>')

    def test_live_package_floors_include_runtime_and_kernel_state(self):
        floors = json.loads((ROOT / 'bpi-r2/package-floors.json').read_text())
        self.assertEqual(floors['installed_build'], '25.12.5-bpi_r2.3')
        self.assertEqual(floors['observed_at'], '2026-10-31T15:18:30Z')
        for name in ('kernel', 'libc', 'curl', 'unbound-daemon', 'kmod-tls'):
            self.assertIn(name, floors['packages'])

    def test_production_only_accepts_exact_vendor_anchor_not_custom_bootstrap(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / 'root'
            anchor = root / 'etc/unbound/root.key'
            anchor.parent.mkdir(parents=True)
            vendor, recovery = Path(directory) / 'vendor', Path(directory) / 'recovery'
            vendor.write_bytes(b'pinned vendor default')
            recovery.write_bytes(b'reviewed fresh-install seed')
            anchor.write_bytes(vendor.read_bytes())
            result = metadata.check_profile(root, 'production', vendor, recovery)
            self.assertTrue(result['requires_preserved_runtime_state'])
            self.assertFalse(result['packaged_seed_is_runtime_acceptance'])
            anchor.write_bytes(recovery.read_bytes())
            with self.assertRaises(ValueError):
                metadata.check_profile(root, 'production', vendor, recovery)
            result = metadata.check_profile(root, 'recovery', vendor, recovery)
            self.assertFalse(result['requires_preserved_runtime_state'])
            anchor.write_bytes(b'unexpected')
            with self.assertRaises(ValueError):
                metadata.check_profile(root, 'recovery', vendor, recovery)

    def test_vendor_anchor_does_not_allow_recovery_script_in_production(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            script = root / 'etc/uci-defaults/99-os298-recovery'
            script.parent.mkdir(parents=True)
            script.write_text('unexpected recovery setup')
            with self.assertRaisesRegex(ValueError, 'recovery bootstrap'):
                metadata.check_profile(root, 'production', root / 'vendor', root / 'recovery')
