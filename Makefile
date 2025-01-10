.PHONY: help
.PHONY: dev
.PHONY: docs
.PHONY: generate
.PHONY: get-static
.PHONY: hook
.PHONY: lint
.PHONY: migrate
.PHONY: migrations
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
  generate                   Create test data.
  get-static                 Download static files.
  hook                       Install pre-commit hook.
  lint                       Run pre-commit hooks on all files.
  migrate                    Run pre-commit hooks on all files.
  migrations                 Run pre-commit hooks on all files.
  styles                     Generate pygments styles.
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
	@poetry run mkdocs serve -a localhost:$(call args, "8080")

generate:
	@poetry run python manage.py create_test_data

get-static:
	@poetry run python manage.py fetch_undine_static

hook:
	@poetry run pre-commit install

lint:
	@poetry run pre-commit run --all-files

migrate:
	@poetry run python manage.py migrate

migrations:
	@poetry run python manage.py makemigrations

styles:
	@poetry run pygmentize -f html -S $(call args, "fruity") -a .highlight > docs/css/pygments.css

test:
	@poetry run pytest -k $(call args, "")

tests:
	@poetry run coverage run -m pytest

tox:
	@poetry run tox

