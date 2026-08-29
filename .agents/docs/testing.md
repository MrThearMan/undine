# Testing

## General rules

Tests verify behavior through public interfaces, not implementation details.
A good test survives when the code underneath changes and breaks when the user behavior changes.

Prefer integration-style tests that exercise real code paths through _public interfaces only_.
A test describes _what_ the system does, not _how_ it does it. If you cannot test an internal detail
through the public interface, simplify instead of testing internals.

## Assertions

Don't assert with a partial substring check when the value's structure or order matters.
A substring match still passes if parts are reordered, duplicated, or a neighboring field is broken.

Prefer exact equality. When part of the value is non-deterministic,
assert the deterministic parts exactly and use an anchored regex
(`re.fullmatch`) for the whole string, with a narrow wildcard only
where the value is genuinely unpredictable.

Note: `pytest.raises(..., match=...)` does an unanchored regex *search*,
so it silently accepts a partial match of the raised exception message.
Use `exact` from `tests/helpers.py` to pin the full message. Only fall back
to a partial or unescaped regex when the message genuinely contains a
non-deterministic part.

## Structure

Follow [code style](./code-style.md).

Group new tests with the existing tests that exercise the same behavior,
don't just append at the end of the file. Put test helpers in a `helpers.py`
at the same directory level as the test file, never inside the test file itself.

Before adding a test, check whether an existing test already covers the
same behavior. Remove or merge true duplicates.

Always use `parametrize_helper` from `tests/helpers.py` when parametrizing with `pytest.mark.parametrize`.

## Mocking

Mock at system boundaries only: external APIs, time, randomness, file system or databases
when a real instance isn't practical. Never mock internal implementation details.
If something is hard to test without mocking internals, redesign the interface.

Always create model test data through factories in `tests/factories/`,
never by instantiating the model directly.

## Coverage

Always measure coverage with `just coverage`. Never scope coverage to a single module.

Don't rely on `just coverage-missing` alone. It reads existing coverage
data rather than running the suite, so if it wasn't preceded by a fresh
`just coverage` run in the same session, it can report 100% based on
stale or incomplete data.

Whenever you change a file, look up that file's line in the `just coverage`
report and check it is at 100% statement and branch coverage after your
change. Do this even if the file wasn't at 100% before your change: don't
assume a file is adequately covered just because that wasn't the number
you started from.

## Mypy

See [mypy-tests.md](mypy-tests.md) for writing and running mypy test cases.
See [mypy-plugin-development.md](mypy-plugin-development.md) for working on the
Undine mypy plugin itself.
