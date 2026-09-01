# List all available commands
help:
    @just -l

# Start the development server in async mode
async port="8000":
    @poetry run python async.py --port {{port}}

# Check undine is installed correctly
check:
    @poetry run python manage.py check undine

# Run Apollo's subgraph compatibility suite
compliance:
    @cd tests/test_federation/compatibility \
      && just up \
      && just compliance \
      && just down

# Run all tests with coverage and show coverage report
coverage:
    @poetry run coverage run -m pytest .
    @poetry run coverage report

# Show files without test coverage
coverage-missing:
    @poetry run coverage report --skip-covered --show-missing

# Print the required versions of main dependencies
deps:
    @poetry run python manage.py get_core_dependencies

# Print top level dependencies
deps-top:
    @poetry show --top-level --only=main --no-truncate

# Print all outdated dependencies
deps-out:
    @poetry show --outdated --format json | jq -r '.[] | [.name, .version, .latest_version] | @tsv' | column -t -s $'\t' -o ' '

# Print all dependencies as a tree
deps-tree:
    @poetry show --tree --no-truncate

# Start the development server in sync mode
dev port="8000":
    @poetry run python manage.py runserver localhost:{{port}}

# Start an mkdocs server
docs port="8080":
    @poetry run mkdocs serve -a localhost:{{port}} -w docs -o --livereload

# Download a pygments code highlighting theme
docs-theme style="fruity":
    @poetry run pygmentize -f html -S {{style}} -a .highlight > docs/css/pygments.css

# Generate testing data for local development
generate:
    @poetry run python manage.py create_test_data

# Install pre-commit hooks
hook:
    @poetry run pre-commit install

# Update all pre-commit hooks
hook-update:
    @poetry run pre-commit autoupdate

# Install all dependencies & make sure they are up to date
install:
    @poetry sync --all-extras --all-groups

# Update GraphiQL import map
importmap:
    @poetry run python manage.py update_import_map

# Run pre-commit hooks on all files
lint:
    @poetry run pre-commit run --all-files

# Generate a new dependency lock file
lock:
    @poetry lock

# Run migrations
migrate:
    @poetry run python manage.py migrate

# Create new migrations
migrations:
    @poetry run python manage.py makemigrations

# Run mypy
mypy dir=".":
    @poetry run mypy {{dir}}

# Generate mypy tests
mypy-test-gen:
    @poetry run python manage.py generate_test_mypy_yml

# Clear mypy cache
mypy-cache-clear:
    @rm -rf .mypy_cache

# Run tests in all supported python and core dependency versions using nox
nox:
    @poetry run nox

# List all available nox sessions
nox-list:
    @poetry run nox --list

# Run all nox sessions concurrently using GNU parallel (jobs: number or "N%" of CPU cores)
nox-parallel jobs="100%":
    @poetry run nox --list --json 2>/dev/null \
      | jq -r '.[].session' \
      | parallel -j{{jobs}} --tag --line-buffer poetry run nox -s {}

# Run a single nox session
nox-one name:
    @poetry run nox -s "{{name}}"

# Run py-spy to profiler on a given process
profile pid:
    @poetry run py-spy --threads --subprocesses --output profile.svg --pid "{{pid}}"

# Find all converter implementations for a given ref
ref-find name:
    @rg -UP '\.register.*\ndef .*\([^)]*(?<!\w)\Q{{name}}\E(?!\w)' undine/converters/impl/

# Run a command in python with django setup
[positional-arguments]
run-python cmd:
    @DJANGO_SETTINGS_MODULE=example_project.project.settings poetry run python -c 'import sys; import django; django.setup(); exec(sys.argv[1])' "$1"

# Run Python code from stdin with django setup
run-python-stdin:
    @DJANGO_SETTINGS_MODULE=example_project.project.settings poetry run python -c 'import sys; import django; django.setup(); exec(sys.stdin.read())'

# Print the GraphQL schema
schema:
    @poetry run python manage.py print_schema

# Collect static files
static:
    @poetry run python manage.py collectstatic --no-input

# Set up local config files
setup-local-configs:
    @poetry run python manage.py setup_local_configs

# Print directory structure
structure dir=".":
    @poetry run python manage.py generate_project_structure "{{dir}}"

# Run all tests with coverage
test dir=".":
    @poetry run pytest {{dir}}

# Run mypy tests
test-mypy name="*":
    @poetry run python manage.py generate_test_mypy_yml --silent
    @RUN_MYPY_TESTS=1 poetry run pytest tests/test_mypy/cases/test_{{name}}.yml

# Run a specific test(s) by keyword (pytest "-k" option)
test-one name:
    @poetry run pytest -k "{{name}}"
