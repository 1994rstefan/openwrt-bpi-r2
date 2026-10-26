"""Fail if defconfig discarded any explicit positive or negative requirement."""

from pathlib import Path
import sys


def check(seed, config):
    expected = {line for line in seed.splitlines()
                if line.startswith("CONFIG_") or line.startswith("# CONFIG_")}
    missing = expected - set(config.splitlines())
    if missing:
        raise ValueError("Missing required settings: " + ", ".join(sorted(missing)))


if __name__ == "__main__":
    check(Path(sys.argv[1]).read_text(), Path(sys.argv[2]).read_text())
