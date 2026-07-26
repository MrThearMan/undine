# Testing

## General conventions

- Never use class-based tests.
- Never use inline imports inside test functions unless absolutely necessary
  (don't assume it's needed before hitting an actual error).
- Put test helpers in a `helpers.py` at the same directory level as the test file,
  never inside the test file itself.
- Always create model test data through factories in `tests/factories/`,
  never by instantiating the model directly.
- Always use `tests.helpers.parametrize_helper` when parametrizing with `pytest.mark.parametrize`.

## Coverage

- `just coverage` runs tests with coverage.
- `just coverage-missing` shows missing coverage.

## Mypy

- See [mypy-tests.md](mypy-tests.md) for writing and running mypy test cases.
- See [mypy-plugin-development.md](mypy-plugin-development.md) for working on the
  Undine mypy plugin itself.
