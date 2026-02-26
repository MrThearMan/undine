# Instructions for Agents

## Commands

- Before you do anything, run `just help` for a list of all common commands
- If using a sandbox, always setup virtualenv with `just install`
- Always use `poetry run` when running python or related commands like pytest

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

## Library settings

- Group library settings in `undine/settings.py` to meaningful sections
- Keep settings documentation in `docs/settings.md` up to date and in alphabetical order
- When removing a setting, add it to `REMOVED_SETTINGS`, mapped to `None`
- When renaming a setting, add the old name to `RENAMED_SETTINGS`, mapped to the new name

## Testing

- Never use class based tests
- Add test helpers to a `helpers.py` file at the same directory level as the test file, never to the test file itself
- Use factories from `tests/factories/` when creating model test data, never create them from the model directly

### Using Nox

- Use nox ONLY when the user EXPLICITLY asks you to use it — otherwise, use virtualenv created by poetry
- Cursor's shell sets `FORCE_COLOR=0` and `NO_COLOR=1`, which makes nox
  fail with conflicting color flags — always unset them first: `unset FORCE_COLOR NO_COLOR`
- Existing nox session virtualenvs live under `.nox/`
  You can use them directly if you need to debug something in them: `.nox/<session-dir>/bin/python <command>`

## Documentation style

- Write in idiomatic english, using simple language
- Use second-person tone with concise paragraphs (1-3 sentences)

### Code examples

- Python code examples must be added with snippets:

```python
-8<- "page/example.py"
```

- GraphQL examples should be added inline

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

- Never commit secrets, credential, or tokens
- Never add or remove dependencies without EXPLICIT permission from the user
- Never remove or repurpose tests without EXPLICIT permission from the user
