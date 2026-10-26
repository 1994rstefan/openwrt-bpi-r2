"""Create a complete CI candidate bundle; never publish or approve deployment."""

import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tarfile


def output(*args):
    return subprocess.check_output(args, text=True).strip()


def identity():
    sha = output("git", "rev-parse", "HEAD")
    if sha != os.environ["EXPECTED_SHA"] or not re.fullmatch(r"[0-9a-f]{40}", sha):
        raise ValueError("Source identity mismatch")
    return {"schema": 1, "repository": os.environ["GITHUB_REPOSITORY"], "source_sha": sha,
            "profile": os.environ["PROFILE"], "upstream_release": "25.12.5",
            "board": "bananapi,bpi-r2", "target": "mediatek/mt7623",
            "run_id": os.environ["GITHUB_RUN_ID"], "run_attempt": os.environ["GITHUB_RUN_ATTEMPT"],
            "workflow_ref": os.environ["GITHUB_WORKFLOW_REF"],
            "installation_approved": False}


def one(pattern):
    matches = list(Path("bin/targets/mediatek/mt7623").glob(pattern))
    if len(matches) != 1:
        raise ValueError(f"Expected exactly one {pattern}, found {len(matches)}")
    return matches[0]


def bundle():
    meta = identity()
    destination = Path("candidate")
    destination.mkdir()
    manifest = one("*.manifest")
    packages = {}
    for line in manifest.read_text().splitlines():
        name, version = line.split(" - ", 1)
        if name in packages:
            raise ValueError("Duplicate manifest package")
        packages[name] = version
    required = set(Path("bpi-r2/required-packages.txt").read_text().splitlines())
    if missing := required - packages.keys():
        raise ValueError(f"Missing required packages: {sorted(missing)}")
    image = one("*-bananapi_bpi-r2-squashfs-sysupgrade.itb")
    sdcard = one("*-bananapi_bpi-r2-sdcard.img.gz")
    fit = output("staging_dir/host/bin/mkimage", "-l", str(image))
    for config in ("config-1", "mt7623n-bananapi-bpi-r2-ds3231"):
        if config not in fit:
            raise ValueError(f"Missing FIT configuration: {config}")
    if not list(Path("bin").rglob("kmod-rtc-ds1307*.apk")):
        raise ValueError("Matching RTC module artifact missing")
    roots = list(Path("build_dir/target-arm_cortex-a7+neon-vfpv4_musl_eabi").glob("root-mediatek"))
    if len(roots) != 1:
        raise ValueError("Cannot identify built root filesystem")
    root = roots[0]
    if (root / "etc/uci-defaults/31_bpi-r2-fit-selectors").exists():
        raise ValueError("Unapproved boot-environment migration included")
    if meta["profile"] == "production":
        for forbidden in ("etc/uci-defaults/99-os298-recovery", "etc/dropbear/authorized_keys", "etc/unbound/root.key"):
            if (root / forbidden).exists():
                raise ValueError(f"Production image contains bootstrap state: {forbidden}")
    for source in (image, sdcard, manifest):
        shutil.copy2(source, destination / source.name)
    shutil.copy2(".config", destination / "config.buildinfo")
    shutil.copy2("bpi-r2/feeds.conf", destination / "feeds.conf")
    shutil.copy2("bpi-r2/required-packages.txt", destination / "required-packages.txt")
    (destination / "fit-layout.txt").write_text(fit + "\n")
    (destination / "builder-packages.txt").write_text(output("dpkg-query", "-W") + "\n")
    (destination / "toolchain.txt").write_text(output("gcc", "--version") + "\n" + output("make", "--version") + "\n")
    meta["kernel"] = packages["kernel"]
    meta["sysupgrade"] = image.name
    meta["sdcard"] = sdcard.name
    meta["feeds"] = {line.split()[1]: output("git", "-C", "feeds/" + line.split()[1], "rev-parse", "HEAD")
                     for line in Path("bpi-r2/feeds.conf").read_text().splitlines()}
    for line in Path("bpi-r2/feeds.conf").read_text().splitlines():
        _, name, source = line.split()
        if meta["feeds"][name] != source.split("^")[1]:
            raise ValueError(f"Feed identity drift: {name}")
    meta["containerfile_sha256"] = hashlib.sha256(Path("bpi-r2/Containerfile").read_bytes()).hexdigest()
    meta["container_image_id"] = os.environ["BUILDER_IMAGE_ID"]
    with tarfile.open(destination / "packages.tar.gz", "w:gz") as archive:
        for path in sorted(Path("bin").rglob("*.apk")):
            archive.add(path, arcname=str(path), recursive=False)
    with tarfile.open(destination / "logs.tar.gz", "w:gz") as archive:
        archive.add("logs", arcname="logs")
    (destination / "provenance.json").write_text(json.dumps(meta, indent=2) + "\n")
    checksums = []
    for path in sorted(destination.iterdir()):
        checksums.append(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}\n")
    (destination / "sha256sums").write_text("".join(checksums))
    name = f"bpi-r2-{meta['profile']}-{meta['run_id']}.{meta['run_attempt']}.tar.gz"
    with tarfile.open(name, "w:gz") as archive:
        archive.add(destination, arcname="candidate")


if __name__ == "__main__":
    if sys.argv[1] == "identity":
        Path("files/etc/os298-firmware.json").write_text(json.dumps(identity(), indent=2) + "\n")
    elif sys.argv[1] == "bundle":
        bundle()
    else:
        raise SystemExit("Unknown metadata operation")
