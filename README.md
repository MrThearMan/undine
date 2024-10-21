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
- [ ] Add tests for optimization
- [ ] Add tests for settings
- [ ] Add tests for errors
- [ ] Add tests for converters
- [ ] Add tests for GenericForeignKeys and GenericRelations
- [ ] Add support for permission checks
- [ ] Add support for pagination
- [ ] Add support for Relay
- [ ] Add utilities for unit testing
- [ ] Sync with graphene-django-query-optimizer
- [ ] Add support for bulk mutations
- [ ] Add documentation for everything!!! (specify later)
- [ ] "mutation_only" inputs, e.g. "CurrentUserDefault"

# Later:
- [ ] Refactor MutationHandler to make less queries when updating nested objects
- [ ] Add support for caching
- [ ] Add support for subscriptions
- [ ] Add support for union types
- [ ] Add support for dataloaders
- [ ] Add support for directives
- [ ] Add support for schema export
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
