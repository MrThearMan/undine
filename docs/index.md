# Undine

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

Undine is a GraphQL library for Django. It's designed to be easy to use and extend,
while providing out-of-the-box solutions for many common issues GraphQL developers face.

## Feature highlights

- Automatic generation of GraphQL types from Django models
- Automatic query optimization
- Logically composable filtering
- Ordering based on enums
- Single and bulk mutations, including relations
- Calculated query fields based on user input
- Hidden and input-only mutation inputs
- Query and Mutation middleware for customizing execution
- Hooks for checking permissions
- Support for Relay Connections and the Relay Node interface
- File uploads based on GraphQL multipart request specification

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
