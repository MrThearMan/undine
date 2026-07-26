# Commands and environment

The `justfile` is the source of truth for repo commands. Read it first.

## Environment setup

If you're in a sandbox, set up the virtualenv with `just install`.

## Running arbitrary Python

Always use `just run-python-stdin` with a heredoc. Do not use `python -c` or create temp files.

```shell
just run-python-stdin <<'EOF' 2>&1
print("Hello World")
EOF
```

## Nox

Use nox ONLY when the user EXPLICITLY asks for it. Otherwise use the poetry virtualenv.
Existing nox session virtualenvs live under `.nox/`. You can invoke them directly for debugging:
`.nox/<session-dir>/bin/python <command>`.
