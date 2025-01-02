# Undine - GraphQL for Django

[![Coverage Status][coverage-badge]][coverage]
[![GitHub Workflow Status][status-badge]][status]
[![PyPI][pypi-badge]][pypi]
[![GitHub][licence-badge]][licence]
[![GitHub Last Commit][repo-badge]][repo]
[![GitHub Issues][issues-badge]][issues]
[![Downloads][downloads-badge]][pypi]
[![Python Version][version-badge]][pypi]

```shell
pip install undine
```

---

**Documentation**: [https://mrthearman.github.io/undine/](https://mrthearman.github.io/undine/)

**Source Code**: [https://github.com/MrThearMan/undine/](https://github.com/MrThearMan/undine/)

**Contributing**: [https://github.com/MrThearMan/undine/blob/main/CONTRIBUTING.md](https://github.com/MrThearMan/undine/blob/main/CONTRIBUTING.md)

---

# Before initial release:
- [ ] Add documentation
- [ ] Run and setup mypy

# Later:
- [ ] Refactor MutationHandler to make less queries when updating nested objects
- [ ] Add caching
- [ ] Add subscriptions
- [ ] Add persisted queries (via sub-app)
- [ ] Add union types
- [ ] Add dataloaders
- [ ] Add directives
- [ ] Add schema export
- [ ] Add debug toolbar integration
- [ ] Add sentry integration


[coverage-badge]: https://coveralls.io/repos/github/MrThearMan/undine/badge.svg?branch=main
[status-badge]: https://img.shields.io/github/actions/workflow/status/MrThearMan/undine/test.yml?branch=main
[pypi-badge]: https://img.shields.io/pypi/v/undine
[licence-badge]: https://img.shields.io/github/license/MrThearMan/undine
[repo-badge]: https://img.shields.io/github/last-commit/MrThearMan/undine
[issues-badge]: https://img.shields.io/github/issues-raw/MrThearMan/undine
[version-badge]: https://img.shields.io/pypi/pyversions/undine
[downloads-badge]: https://img.shields.io/pypi/dm/undine

[coverage]: https://coveralls.io/github/MrThearMan/undine?branch=main
[status]: https://github.com/MrThearMan/undine/actions/workflows/test.yml
[pypi]: https://pypi.org/project/undine
[licence]: https://github.com/MrThearMan/undine/blob/main/LICENSE
[repo]: https://github.com/MrThearMan/undine/commits/main
[issues]: https://github.com/MrThearMan/undine/issues
