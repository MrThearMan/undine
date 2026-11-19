# ruff: noqa: INP001
"""
List open issues that have no open blocking issues, and sync the 'ready to start' label for them.

Blocking issues are GitHub's native issue dependencies ("blocked by").
Needs the GitHub CLI ('gh') with access to the repository.

Usage:
    python .github/scripts/ready_issues.py           # Print the ready issues.
    python .github/scripts/ready_issues.py --sync    # Also add and remove the 'ready to start' label.
    python .github/scripts/ready_issues.py --sync --dry-run
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from dataclasses import dataclass

READY_LABEL = "ready to start"

QUERY = """
query($owner: String!, $name: String!, $cursor: String) {
  repository(owner: $owner, name: $name) {
    issues(first: 100, after: $cursor, states: [OPEN]) {
      pageInfo { hasNextPage endCursor }
      nodes {
        number
        title
        labels(first: 50) { nodes { name } }
        blockedBy(first: 100) { nodes { number state } }
      }
    }
  }
}
"""

READY_QUERY = """
query($owner: String!, $name: String!, $cursor: String, $label: String!) {
  repository(owner: $owner, name: $name) {
    issues(first: 100, after: $cursor, labels: [$label]) {
      pageInfo { hasNextPage endCursor }
      nodes { number state }
    }
  }
}
"""


@dataclass
class Issue:
    number: int
    title: str
    labels: set[str]
    open_blockers: list[int]

    @property
    def ready(self) -> bool:
        return not self.open_blockers


def gh(*args: str) -> str:
    return subprocess.run(["gh", *args], check=True, capture_output=True, text=True).stdout  # noqa: S603,S607


def get_repo() -> tuple[str, str]:
    repo = os.environ.get("GITHUB_REPOSITORY")
    if not repo:
        repo = gh("repo", "view", "--json", "nameWithOwner", "--jq", ".nameWithOwner")
    owner, name = repo.strip().split("/")
    return owner, name


def paginate(query: str, owner: str, name: str, **variables: str) -> list[dict]:
    nodes: list[dict] = []
    cursor: str | None = None
    while True:
        args = ["api", "graphql", "-f", f"query={query}", "-f", f"owner={owner}", "-f", f"name={name}"]
        for key, value in variables.items():
            args += ["-f", f"{key}={value}"]
        if cursor is not None:
            args += ["-f", f"cursor={cursor}"]
        page = json.loads(gh(*args))["data"]["repository"]["issues"]
        nodes += page["nodes"]
        if not page["pageInfo"]["hasNextPage"]:
            return nodes
        cursor = page["pageInfo"]["endCursor"]


def get_open_issues(owner: str, name: str) -> list[Issue]:
    return [
        Issue(
            number=node["number"],
            title=node["title"],
            labels={label["name"] for label in node["labels"]["nodes"]},
            open_blockers=sorted(b["number"] for b in node["blockedBy"]["nodes"] if b["state"] == "OPEN"),
        )
        for node in paginate(QUERY, owner, name)
    ]


def edit_label(owner: str, name: str, number: int, *, add: bool, dry_run: bool) -> None:
    action = "Add" if add else "Remove"
    print(f"{action} '{READY_LABEL}' on #{number}")  # noqa: T201
    if dry_run:
        return
    flag = "--add-label" if add else "--remove-label"
    gh("issue", "edit", str(number), "--repo", f"{owner}/{name}", flag, READY_LABEL)


def sync(owner: str, name: str, issues: list[Issue], *, dry_run: bool) -> None:
    for issue in issues:
        has_label = READY_LABEL in issue.labels
        if issue.ready and not has_label:
            edit_label(owner, name, issue.number, add=True, dry_run=dry_run)
        elif not issue.ready and has_label:
            edit_label(owner, name, issue.number, add=False, dry_run=dry_run)

    # Closed issues are never ready.
    for node in paginate(READY_QUERY, owner, name, label=READY_LABEL):
        if node["state"] != "OPEN":
            edit_label(owner, name, node["number"], add=False, dry_run=dry_run)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--sync", action="store_true", help=f"Add and remove the '{READY_LABEL}' label.")
    parser.add_argument("--dry-run", action="store_true", help="With --sync, print the changes only.")
    args = parser.parse_args()

    owner, name = get_repo()
    issues = get_open_issues(owner, name)

    ready = [issue for issue in issues if issue.ready]
    print(f"{len(ready)} of {len(issues)} open issues are ready:")  # noqa: T201
    for issue in sorted(ready, key=lambda i: i.number):
        print(f"  #{issue.number} {issue.title}")  # noqa: T201

    if args.sync:
        sync(owner, name, issues, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
