# ruff: noqa: INP001
"""
Check a new release version and add it to the version dropdown in the bug report issue template.

The dropdown keeps all patch versions of the latest minor version
and the newest patch version of the minor version before it.

Usage:
    python .github/scripts/bump_version.py 0.5.2
"""

from __future__ import annotations

import argparse
import re
import sys
import tomllib
from pathlib import Path
from typing import NamedTuple

ROOT = Path(__file__).resolve().parents[2]
PYPROJECT = ROOT / "pyproject.toml"
BUG_REPORT = ROOT / ".github" / "ISSUE_TEMPLATE" / "bug_report.yml"

VERSION_PATTERN = re.compile(r"(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)")
VERSION_OPTIONS_PATTERN = re.compile(
    r"(?P<head>    id: version\n(?:.*\n)*?      options:\n)(?P<options>(?:        - \".*\"\n)+)",
)


class Version(NamedTuple):
    major: int
    minor: int
    patch: int

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"


class VersionError(Exception): ...


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("version", help="The new version, e.g. '0.5.2'.")
    arguments = parser.parse_args()

    try:
        new_version = parse_version(arguments.version)
        check_newer_than_current(new_version)
        update_bug_report(new_version)

    except VersionError as error:
        print(error, file=sys.stderr)  # noqa: T201
        sys.exit(1)


def parse_version(value: str) -> Version:
    match = VERSION_PATTERN.fullmatch(value)
    if match is None:
        msg = f"Version '{value}' is not in the format 'MAJOR.MINOR.PATCH'."
        raise VersionError(msg)

    return Version(major=int(match["major"]), minor=int(match["minor"]), patch=int(match["patch"]))


def check_newer_than_current(new_version: Version) -> None:
    content = PYPROJECT.read_text(encoding="utf-8")
    pyproject = tomllib.loads(content)
    current_version = parse_version(pyproject["project"]["version"])

    if new_version <= current_version:
        msg = f"New version '{new_version}' must be greater than the current version '{current_version}'."
        raise VersionError(msg)


def update_bug_report(new_version: Version) -> None:
    content = BUG_REPORT.read_text(encoding="utf-8")

    match = VERSION_OPTIONS_PATTERN.search(content)
    if match is None:
        msg = f"Could not find the version dropdown options in '{BUG_REPORT}'."
        raise VersionError(msg)

    old_versions = [parse_version(value) for value in re.findall(r'"(.*)"', match["options"])]
    versions = supported_versions([*old_versions, new_version])
    options = "".join(f'        - "{version}"\n' for version in versions)

    new_content = content[: match.start("options")] + options + content[match.end("options") :]
    BUG_REPORT.write_text(new_content, encoding="utf-8")


def supported_versions(versions: list[Version]) -> list[Version]:
    newest_first = sorted(set(versions), reverse=True)
    latest = newest_first[0]

    latest_minor = [version for version in newest_first if version[:2] == latest[:2]]
    older_minors = (version for version in newest_first if version[:2] < latest[:2])
    previous_minor = next(older_minors, None)

    if previous_minor is None:
        return latest_minor
    return [*latest_minor, previous_minor]


if __name__ == "__main__":
    main()
