#!/usr/bin/env python3
"""M-03: VERSION is authoritative; all published metadata must match it."""
import re
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def main():
    version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    assert re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", version), version
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert project["project"]["version"] == version
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    index_version = re.search(r"^- \*\*([0-9]+\.[0-9]+\.[0-9]+)\*\*", changelog, re.M)
    detail_version = re.search(r"^## \[([0-9]+\.[0-9]+\.[0-9]+)\]", changelog, re.M)
    assert index_version and index_version.group(1) == version
    assert detail_version and detail_version.group(1) == version
    skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    skill_version = re.search(r"<!-- skill-version-source: VERSION; skill-version: ([0-9.]+) -->", skill)
    assert skill_version and skill_version.group(1) == version
    print(f"PASS: M-03 version metadata consistent at {version}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
