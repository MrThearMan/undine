# Mypy tests

The Undine mypy plugin is tested with [pytest-mypy-plugins].

[pytest-mypy-plugins]: https://github.com/typeddjango/pytest-mypy-plugins

## Writing cases

Write each case as an individual file under `tests/test_mypy/`,
then regenerate the yml files with `just mypy-test-gen`.
Do not manually edit the yml files `tests/test_mypy/cases/`.
Use `typing.assert_type` instead of `reveal_type` to check types.

## Running cases

Run a single test with `just test-mypy <name>`, where `<name>` is the test file name
without the `.py` extension.

Note: `--no-incremental` on the command line is **not** enough to guarantee a fresh run.
Mypy still consults `.mypy_cache/` for imported modules. Always run `just mypy-cache-clear`
when a plugin change is expected to affect an already-checked file, or you'll chase
ghost errors that no longer exist in the current code.

## `### out` line numbers

The `### out` block's `main:N:` line numbers count from the first line of Python
**after the module docstring closes**, not from the top of the source file.
When adding or reshuffling a case, run it once, copy the actual `main:N:` values from
the output, and paste them in. Guessing offsets wastes iterations.
`poetry run mypy path/to/case.py` reports errors relative to the source file's line
numbers. Those are **not** the ones to paste into `### out`. Only the yml runner
produces `main:N:` numbers.
