.PHONY: help
.PHONY: dev
.PHONY: docs
.PHONY: hook
.PHONY: lint
.PHONY: migrate
.PHONY: migrations
.PHONY: mypy
.PHONY: test
.PHONY: tests
.PHONY: tox
.PHONY: Makefile

# Trick to allow passing commands to make
# Use quotes (" ") if command contains flags (-h / --help)
args = `arg="$(filter-out $@,$(MAKECMDGOALS))" && echo $${arg:-${1}}`

# If command doesn't match, do not throw error
%:
	@:

define helptext

  Commands:

  dev                        Serve manual testing server
  docs                       Serve mkdocs for development.
  get-static                 Download static files.
  get-graphiql               Download graphiql.
  get-react                  Download react.
  get-explorer-plugin        Download graphiql explorer plugin.
  hook                       Install pre-commit hook.
  lint                       Run pre-commit hooks on all files.
  migrate                    Run pre-commit hooks on all files.
  migrations                 Run pre-commit hooks on all files.
  mypy                       Run mypy on all files.
  test <name>                Run all tests maching the given <name>
  tests                      Run all tests with coverage.
  tox                        Run all tests with tox.

  Use quotes (" ") if command contains flags (-h / --help)
endef

export helptext

help:
	@echo "$$helptext"

dev:
	@poetry run python manage.py runserver localhost:8000

docs:
	@poetry run mkdocs serve -a localhost:8080

get-static: get-graphiql get-react get-explorer-plugin

get-graphiql:
	@curl https://unpkg.com/graphiql@3.2.3/graphiql.min.js --create-dirs -o ./undine/static/undine/js/graphiql.min.js
	@curl https://unpkg.com/graphiql@3.2.3/graphiql.min.css --create-dirs -o ./undine/static/undine/css/graphiql.min.css

get-react:
	@curl https://unpkg.com/react@18.3.1/umd/react.development.js --create-dirs -o ./undine/static/undine/js/react.development.js
	@curl https://unpkg.com/react-dom@18.3.1/umd/react-dom.development.js --create-dirs -o ./undine/static/undine/js/react-dom.development.js

get-explorer-plugin:
	@curl https://unpkg.com/@graphiql/plugin-explorer@3.0.2/dist/index.umd.js --create-dirs -o ./undine/static/undine/js/plugin-explorer.umd.js
	@curl https://unpkg.com/@graphiql/plugin-explorer@3.0.2/dist/style.css --create-dirs -o ./undine/static/undine/css/plugin-explorer.css

hook:
	@poetry run pre-commit install

lint:
	@poetry run pre-commit run --all-files

migrate:
	@poetry run python manage.py migrate

migrations:
	@poetry run python manage.py makemigrations

mypy:
	@poetry run mypy undine/

test:
	@poetry run pytest -k $(call args, "")

tests:
	@poetry run coverage run -m pytest

tox:
	@poetry run tox

