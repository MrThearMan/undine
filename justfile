# List all available commands
help:
    @just -l

# Check undine is installed correctly
check:
    @poetry run python manage.py check undine

# Start the development server
dev port="8000":
    @poetry run python manage.py runserver localhost:{{port}}

# Start the development server using uvicorn
dev-async port="8000":
    @poetry run uvicorn example_project.project.asgi:application --reload --host localhost --port {{port}}

# Start the docs server
docs port="8080":
    @poetry run mkdocs serve -a localhost:{{port}} -o

# Download a pygments code highlighting theme
docs-theme style="fruity":
    @poetry run pygmentize -f html -S {{style}} -a .highlight > docs/css/pygments.css

# Generate testing data
generate:
    @poetry run python manage.py create_test_data

# Install pre-commit hooks
hook:
    @poetry run pre-commit install

# Update GraphiQL import map
importmap:
    @poetry run python manage.py update_import_map

# Run pre-commit hooks
lint:
    @poetry run pre-commit run --all-files

# Run migrations
migrate:
    @poetry run python manage.py migrate

# Create new migrations
migrations:
    @poetry run python manage.py makemigrations

# Run tests in all supported python versions using nox
nox:
    @poetry run nox

# Run py-spy to profiler on a given process
profile pid:
    @poetry run py-spy --threads --subprocesses --output profile.svg --pid "{{pid}}"

# Print the GraphQL schema
schema:
    @poetry run python manage.py print_schema

# Collect static files
static:
    @poetry run python manage.py collectstatic --no-input

# Sync dependencies
sync:
    @poetry sync --all-extras

# Run a specific test by name
test name:
    @poetry run pytest -k "{{name}}"

# Run all tests
tests:
    @poetry run coverage run -m pytest
