# Instructions for Agents

## Domain

- Domain is explained in [CONTEXT.md](CONTEXT.md). Please read this to understand the domain language used in the project.

## Commands

- Before you do anything, always read `justfile` to get a list of all available commands. USE THEM WHEN APPLICABLE!
- If using a sandbox, always setup virtualenv with `just install`
- If you need to run arbitrary python, always use `just run-python-stdin` with a heredoc. DO NOT USE `python -c`, DO NOT CREATE TEMP FILES!

```shell
just run-python-stdin <<'EOF' 2>&1
print("Hello World")
EOF
```

## Code style

- Never add module docstrings and only add docstrings to classes, functions, or variables when necessary
- Prefer using unabbreviated names for classes, functions, or variables
- Prefer constructing specially formatted strings using functions designed for that purpose,
  e.g. use `urllib.parse.urlencode` to create query strings
- Prefer making all function arguments keyword only when there are more than 3 of them
  (excluding `self` in methods), or there are any of the same type
- Prefer not returning tuples from functions; create separate functions that are called
  in the parent instead, or return a structured object like a `dataclass` or a `TypedDict` instead
- Prefer assigning class instances or function return values to variables
  before passing them as arguments or using them in comparisons

## The user is your friend

- If you encounter something that is unclear, ambiguous, unplanned, conflicting,
  or you feel like you are going down a rabbit hole, always default to asking the user
  to help with the issue rather than trying to solve it yourself.
  You can suggest trying to solve it, but always ask the user first before burning context.

## Library settings

- Group library settings in `undine/settings.py` to meaningful sections
- Keep settings documentation in `docs/settings.md` up to date and in alphabetical order
- When removing a setting, add it to `REMOVED_SETTINGS`, mapped to `None`
- When renaming a setting, add the old name to `RENAMED_SETTINGS`, mapped to the new name

## Testing

- Never use class based tests
- Never use inline imports inside test functions (unless absolutely necessary, but do not assume it before running into an error)
- Add test helpers to a `helpers.py` file at the same directory level as the test file, never to the test file itself
- Always use factories from `tests/factories/` when creating model test data, never create them from the model directly
- Always use `tests.helpers.parametrize_helper` to when parametrizing tests using `pytest.mark.parametrize`

### Coverage

- Run `just coverage` to run tests with coverage
- Run `just coverage-missing` to check for missing coverage

### Using Nox

- Use nox ONLY when the user EXPLICITLY asks you to use it — otherwise, use virtualenv created by poetry
- Cursor's shell sets `FORCE_COLOR=0` and `NO_COLOR=1`, which makes nox
  fail with conflicting color flags — always unset them first: `unset FORCE_COLOR NO_COLOR`
- Existing nox session virtualenvs live under `.nox/`
  You can use them directly if you need to debug something in them: `.nox/<session-dir>/bin/python <command>`

### Mypy tests

- Do not manually write mypy tests in `tests/test_mypy/test_mypy.yml`!
- Write mypy tests in individual files in `tests/test_mypy/cases` and generate the test file with `just mypy-test-gen`
- Use `typing.assert_type` instead of `reveal_type` to check types
- See `generate_test_mypy_yml.py` for how the test file is generated
- When necessary, you can clear the mypy cache with `just mypy-cache-clear`

#### Incremental safety

- Plugin hooks must be **incremental-cache-safe**: their results are cached and re-used
  across daemon runs, so they must not depend on global state or on mypy AST attributes
  that aren't serialized. `info.defn.*` (`ClassDef.keywords`, `.decorators`, `.metaclass`,
  `.defs`, `.analyzed`) is a common trap — it's populated only during fresh analysis and
  reads as empty on cache-loaded `TypeInfo`s (see `mypy/nodes.py::ClassDef.serialize`),
  silently corrupting downstream checks
- Persist anything you need across runs into `TypeInfo.metadata` (a `dict[str, JsonDict]`
  reserved for plugins and always serialized); populate it during the fresh-analysis
  `base_class_hook`, then read from metadata everywhere else. This is the same pattern
  mypy's own `attrs` and `dataclasses` plugins use

### Plugin testing

- The `### out` block's `main:N:` line numbers count from the **first line of Python
  after the module docstring closes**, not from the top of the source file. When adding
  or reshuffling a case, just run it once, copy the actual `main:N:` values from the
  output, and paste them in. Guessing at offsets wastes iterations
- `poetry run mypy path/to/case.py` will report errors relative to the *source* file's
  line numbers — those are **not** the ones to paste into `### out`. Only the yml runner
  produces `main:N:` numbers. Regenerate the yml and run a single test with
  `just test-mypy <name>`, where `<name>` is the test file name without the `.py` extension
- `--no-incremental` on the command line is **not** enough to guarantee a fresh run —
  mypy still consults `.mypy_cache/` for imported modules. Always `just mypy-cache-clear`
  when a plugin change is expected to affect an already-checked file, or you'll chase
  ghost errors that no longer exist in the current code
- When a hook seems not to fire, insert `print(f"...", file=sys.stderr)` inside it and
  run mypy once — mypy captures plugin stderr and shows it inline in the error output
  (via pytest-mypy-plugins the print lines appear as spurious "diff" lines, which is
  actually convenient for confirming the hook ran)
- To see what type mypy resolved for an expression during plugin work, temporarily
  swap `assert_type(x, ...)` for `reveal_type(x)`

## Documentation style

- Write in idiomatic english, using simple language
- Use second-person tone with concise paragraphs (1-3 sentences)
- Order sections in teaching order (foundation first, then what the user applies), not alphabetical or spec order
- Show, don't narrate: a code snippet plus a rendered output block teaches more than prose
- Prefer subsections over Markdown tables
- Give each first-class API entity its own subsection named after it
- Cut design-decision justification and internal implementation detail
- Don't preemptively enumerate errors or edge cases the user will hit once and understand from the error message

### Page structure

- Every page starts with a `description:` line, a blank line, then the `# Title`:

```markdown
description: Documentation on queries in Undine.

# Queries
```

- Open the body with a short paragraph stating what the page covers, linking to related pages inline
- Use `##` for top-level topics, `###` for subsections, `####` only when necessary
- Wrap every mention of a code entity (class, method, field, module, path) in backticks — including repeat mentions
- Bold a new concept the first time it's introduced; use backticks (not italics) for anything code-shaped
- Follow the pattern: brief prose → code snippet → the resulting output

### Code examples

- Python code examples must be added with snippets:

```python
-8<- "page/example.py"
```

- Snippet directory mirrors the page name with underscores: `docs/file-upload.md` → `docs/snippets/file_uploads/`
- Snippet file naming: `<entity>_<feature>.py`, e.g. `field_alias.py`, `filterset_decorator.py`
- One snippet per concept — don't bundle multiple concepts into a single snippet file
- When a Python definition produces schema, always show the generated `graphql` block below it
- Use fenced blocks with an explicit language: `python`, `graphql`, `json`, `pycon` (REPL with `>>>`), `shell`
- Use `hl_lines="..."` on the fence (not the snippet directive) to point at the key lines
- GraphQL examples should be added inline

### Notes and collapsibles

- Use `> ` blockquotes for short inline notes, warnings, and "experimental feature" callouts. Never use `!!! note` admonitions
- Use `/// details | Title` ... `///` blocks for collapsible content: expected responses, side discussions, per-entry reference sections
- Setting entries in `docs/settings.md` use this exact shape:

```markdown
/// details | `SETTING_NAME`
    attrs: {id: setting_name}

Type: `bool` | Default: `False`

Description of the setting.

///
```

### Links

- Internal links should use markdown file links:

```markdown
[SETTING_NAME](settings.md#setting_name)
```

- External links should open in a new tab, and put the actual link on a new line:

```markdown
This is a [link]{:target="_blank"}

[link]: https://example.com/
```

## Boundaries

- Never ever, under any circumstances, run `poetry publish`, run `mkdocs gh-deploy`, or change project version number
- Never make git commits, let me handle that
- Never put secrets, credential, or tokens in git tracked files
- Never add or remove dependencies without EXPLICIT permission from the user
- Never remove or repurpose tests without EXPLICIT permission from the user
