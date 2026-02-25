# Instructions for Agents

## Description

A GraphQL server library for Django.

## Commands

Always read [justfile](justfile) for a list of all common commands.

If using a sandbox, always setup virtualenv with `just install`.

Always use `poetry run` when running python or related commands like pytest.

## Dependencies

Core dependencies: `poetry show --top-level --only=main`.

All dependencies: `poetry show --tree`.

Read [pyproject.toml](pyproject.toml) for minimum supported versions.

## Structure

Django library with and example Django project. Some key paths:

```
├── docs/                       # Documentation
│   ├── snippets/               # Documentation code snippets
│   │   └── <page>/             # Snippets for a specific page
│   └── <page>.md               # A single documentation page
│
├── example_project/            # Example project for testing
│   ├── app/                    # Django app for testing
│   │   ├── management/         # Private Django management commands
│   │   └── templates/app/      # Private Django templates
│   └── project/                # Django project
│
├── pytest_undine/              # Pytest plugin for the library
│
├── tests/                      # All tests
│
└── undine/                     # Core library
    ├── integrations/           # Integrations with other libraries
    ├── management/             # Public Django management commands
    ├── templates/undine/       # Public Django templates
    ├── dataclasses.py          # Project specific dataclasses
    ├── exceptions.py           # Project specific exceptions
    ├── settings.py             # Library settings
    └── types.py                # Project specific types
```

## Code style

Never add module docstrings and only add docstrings to classes and functions when necessary.

Prefer using unabbreviated names for classes, functions, or variables, even if this would make the name a bit verbose.
You can still use established abbreviations already in the codebase.

Prefer constructing specially formatted strings using functions designed for that purpose,
e.g. use `urllib.parse.urlencode` to create query strings.

Prefer making all function or method arguments keyword only when there are more than 3 of them
(excluding method self), or there are any of the same type.

Prefer not returning tuples from functions or methods.
Create separate functions that are called in the parent,
or return a structured object like a dataclass or a `TypedDict` instead.

Prefer assigning class instances or function return values to variables
before passing them as arguments or using them in comparisons.

## Library settings

Group library settings in `undine/settings.py` to meaningful sections.

Keep settings documentation in `docs/settings.md` up to date and in alphabetical order.

When removing a setting, add it to `REMOVED_SETTINGS`, mapped to `None`.

When renaming a setting, add the old name to `RENAMED_SETTINGS`, mapped to the new name.

## Testing

Always add or update tests for the code you are adding or changing.

Never remove or repurpose tests without EXPLICIT permission from the user.

Never use class based tests.

Loosely mirror project structure.

Break test files into sections with comments.

Add test helpers to a `helpers.py` file at the same directory level as the test file, never to the test file itself.

Use factories from `tests/factories/` when creating model test data, never create them from the model directly.

Always run `just lint` before running tests.

### Using Nox

Use nox ONLY when the user EXPLICITLY asks you to use it.
Otherwise, use virtualenv created by poetry.

Cursor's shell sets `FORCE_COLOR=0` and `NO_COLOR=1`, which makes nox
fail with conflicting color flags. Always unset them first:

```bash
unset FORCE_COLOR NO_COLOR
```

Existing nox session virtualenvs live under `.nox/`.
You can use them directly if you need to debug something in them:

```bash
.nox/<session-dir>/bin/python <command>
```

## Documentation style

Use second-person tone with concise paragraphs (1-3 sentences).

Use blockquotes for important notes/caveats.

### Code examples

Python code examples must be added with snippets:

```python
-8<- "page/example.py"
```

GraphQL examples should be added inline.

### Links

Internal links should use markdown file links:

```markdown
[SETTING_NAME](settings.md#setting_name)
```

External links should open in a new tab, and put the actual link on a new line:

```markdown
This is a [link]{:target="_blank"}

[link]: https://example.com/
```

## Boundaries

Never commit secrets, credential, or tokens.

Never add or remove dependencies.
