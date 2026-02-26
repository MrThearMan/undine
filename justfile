# List all available commands
help:
    @just -l

# Start the development server in async mode
async port="8000":
    @poetry run python async.py

# Check undine is installed correctly
check:
    @poetry run python manage.py check undine

# Run all tests with coverage
coverage:
    @poetry run coverage run -m

# Print the required versions of main dependencies
deps:
    @poetry run python manage.py get_core_dependencies

# Print top level dependencies
deps-top:
    @poetry show --top-level --only=main --no-truncate

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

# Run tests in all supported python and core dependency versions using nox
nox:
    @poetry run nox

# List all available nox sessions
nox-list:
    @poetry run nox --list

# Run a single nox session
nox-one name:
    @poetry run nox -s "{{name}}"

# Run py-spy to profiler on a given process
profile pid:
    @poetry run py-spy --threads --subprocesses --output profile.svg --pid "{{pid}}"

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
    @poetry run pytest "{{dir}}"

# Run a specific test(s) by keyword (pytest "-k" option)
test-one name:
    @poetry run pytest -k "{{name}}"
