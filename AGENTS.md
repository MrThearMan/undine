# Instructions for Agents

Undine is a batteries-included GraphQL library for Django. See [CONTEXT.md](CONTEXT.md) for the domain language.

## Before you start any task

- Read the `justfile` to see the available commands and use them when applicable.
- If something is unclear, ambiguous, conflicting, or you feel like you're going down a rabbit hole,
  ask the user before burning context. You may suggest an approach, but ask first.

## Boundaries

Never do any of the following without explicit permission from the user:

- **Publish or release.** No `poetry publish`, `gh release create`, `mkdocs gh-deploy`, `docker push`,
  creating or pushing tags, or changing the project version number.
- **Rewrite git history or push.** No `git push` (in any form), `git commit`,
  `git commit --amend`, `git rebase`, `git reset --hard`, `git filter-branch`,
  `git filter-repo`, or deleting/moving branches or tags.
- **Delete or discard work.** No `rm -rf`, `git clean`, `git checkout .` /
  `git restore .` on a dirty tree, dropping the dev database, or overwriting
  lockfiles, migrations, or fixtures.
- **Change dependencies.** No adding or removing packages, no regenerating `poetry.lock`.
- **Commit secrets.** No credentials or tokens in git-tracked files.

## Detailed guides

Load the guide that matches what you're doing:

- [Commands and environment](.agents/docs/commands.md) — running python, virtualenvs, nox
- [Code style](.agents/docs/code-style.md) — naming, docstrings, function signatures
- [Testing](.agents/docs/testing.md) — pytest conventions and coverage
- [Mypy tests](.agents/docs/mypy-tests.md) — writing and running cases under `tests/test_mypy/`
- [Mypy plugin development](.agents/docs/mypy-plugin-development.md) — working on the Undine mypy plugin
- [Documentation style](.agents/docs/documentation.md) — writing pages under `docs/`
- [Library settings](.agents/docs/library-settings.md) — editing `undine/settings.py`
