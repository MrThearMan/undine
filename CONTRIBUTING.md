# Contributing

Thank you for your interest in contributing!

To start, please read the library [docs] thoroughly.
If you don't find what you are looking for, proceed with the steps below.

[docs]: https://mrthearman.github.io/undine/

## I found a bug!

Please file a [bug report]. If you are not using the latest version of the library,
please upgrade and see if that fixes the issue. If not, please create a minimal example
that demonstrates the bug and instructions on how to create that setup from a new virtual
environment. Also include any error tracebacks (unabridged when possible). This will help
a lot when diagnosing the bug. Do not use pictures to include the traceback.

[bug report]: https://github.com/MrThearMan/undine/issues/new?template=bug_report.yml

## I have a feature request!

You can suggest new features to be implemented via a [feature request].
You can ask me to implement it or work on it yourself but all features should
be discussed and agreed upon first before any coding is done.

[feature request]: https://github.com/MrThearMan/undine/issues/new?template=feature_request.yml

## I have a question!

Please ask it in the [discussions section] instead of creating an issue.
If your question warrants an issue, I'll ask you to create it.
Questions about clarifying documentation are appreciated!

[discussions section]: https://github.com/MrThearMan/undine/discussions

## Creating a pull request

Once you have created a [feature request], we have agreed on an implementation,
and you wish to work on it, follow these steps to create a pull request.

[feature request]: https://github.com/MrThearMan/undine/issues/new?template=feature_request.yml

1. [Fork the repository][fork].
2. Clone your fork and create a new branch from the `main` branch.
3. [Set up the environment](#setting-up-the-environment).
4. Make changes and write tests following [these guidelines](#guidelines-for-writing-code).
5. Add documentation when applicable following [these guidelines](#guidelines-for-writing-documentation).
6. Push the changes to your fork.
7. Create a [pull request] targeting the main branch.
8. Sit back while your pull request is [reviewed](#code-review-process).

[pull request]: https://github.com/MrThearMan/undine/compare
[fork]: https://github.com/MrThearMan/undine/fork

Note that a pull request should always be aimed at solving a single issue.
If you want multiple issues solved, make separate pull requests for each.
Corrections for spelling mistakes are the exception, since I make so many of those...

Pull requests should be kept as small as possible while following the guidelines
mentioned above. Smaller pull request are easier to review and test which helps
them get merged.

## Code review process

Pull requests will be reviewed automatically and manually.

In the automated phase, [GitHub Actions] will run testing pipelines for all supported
operating systems and python versions, and [pre-commit CI] will check linting rules.
If you encounter any errors, try to fix them based on what the pipelines tell you.
If coverage is lowered, add tests, noting the guidelines [here](#guidelines-for-writing-code).
Don't be afraid to ask for advice if you're unsure what is wrong.

[Github Actions]: https://github.com/features/actions
[pre-commit ci]: https://pre-commit.ci/

> Note for first-time contributors: Checks are not allowed to run automatically for
> first-time contributors, so you'll need me to approve them each time you push new code.

In the manual phase, I will review the pull request by adding comments with suggestions
for changes. If you agree with the suggestions, implement them and push the changes to
you fork — the pull request will be updated automatically. You can either amend your previous
commits or add more commits, either is fine. If you disagree with the suggestions, provide
your reasons for disagreeing and we can discuss what to do.

Once all automated checks have passed and I have accepted the pull request, your code will be
merged to the `main` branch. Any related issues should be closed as completed.
I'll usually make a [new release](#creating-a-new-release) after each new feature,
but if not, you can also ask for one.

## Creating a new release

1. Increment the version in `pyproject.toml`, loosely following [semantic versioning] rules.
2. Push the change to the `main` branch with the commit message `Bump version`.
3. [Draft a new release] on GitHub.
   - Use `v{version}` (e.g. v1.2.3) for the tag name and `Release {version}` for the release title,
     using the same version that's in `pyproject.toml`. Note that the release will be made
     with the `pyproject.toml` version and not the tag name!
   - Fill in the release description.
   - Add any attachments when applicable.
4. Publish the release. This will start the `release` pipeline in [GitHub Actions].
5. Check that the release pipeline was successful. If not, delete the tag from origin
   with `git push --delete origin {tag_name}` and fix the issue before trying again.

[semantic versioning]: https://semver.org/
[Draft a new release]: https://github.com/MrThearMan/undine/releases/new
[Github Actions]: https://github.com/features/actions

## Setting up the environment

1. Install [Poetry].
2. Install [Just].
3. Run `poetry install` to create a virtual environment and install project dependencies.
4. Run `just hook` to install the [pre-commit] hooks.

[Poetry]: https://python-poetry.org/docs/#installation
[Just]: https://github.com/casey/just
[pre-commit]: https://pre-commit.com/

Run `just help` to list all existing development commands and their descriptions.

## Testing

Tests can be run with `just tests` and individual tests with `just test <test_name>`.
This will run tests in you [local environment](#setting-up-the-environment).

You can also test your code in multiple environments with [nox]. To do this, you must
install python interpreters for all python version the library supports and then run
`just nox`.

[nox]: https://github.com/wntrblm/nox

Linting can be run on-demand with `just lint` or automatically before commits
when installed with `just hook`.

## Guidelines for writing code

### All code should be tested with 100% coverage

Do not write tests simply to archive 100% coverage. Instead, try to write tests for all the ways the
feature could be used (use cases), including ways that should not work, and then test for coverage.
If you find uncovered code, see if you can remove it, or maybe you simply missed a use case.
You should always need more tests to cover all use cases than to achieve 100% coverage.

Adding `# pragma: no cover` to a line of code will ignore it from coverage results, but this
should be used _**very**_ sparingly, as this can lead to undocumented behavior if you are not careful.
An example of a line that might be ignored like this is an exception
that is raised at the end of a match statement, where its cases cover all possible inputs
(basically a statement that should never be reached).

### All code should be typed when possible

Tests are an exception to this.

Make sure the typing construct used is supported in all python versions
the library supports. If not, you should reconsider if there is an older alternative,
or if there is a backport that can be installed conditionally for the older versions.
In these cases, the type should be added to the `undine/typing.py` file, so that the
import logic between the backport and the standard library is contained in one place.

Create all custom types in `undine/typing.py` and import them from there.
This helps avoids circular imports and prevents creating duplicate types.

Use of `TypedDict` is encouraged where dicts would be used.

### All "public" functions, methods, and classes should include a docstring

"Public" here means that the piece of code is intended to be used by the library users
directly, and not inside the library itself.

Docstrings should be written in [reStructuredText format].

[reStructuredText format]: https://peps.python.org/pep-0287/

Code that is short and _clearly_ self-documenting does not necessarily need a docstring.
As an example, `def sum(i: int, j: int) -> int: return i + j` does not need a docstring.
This applies more broadly to arguments, e.g., when a function might need a docstring, the arguments
might not need explicit documentation.

Keep the docstring to the point. Each line of documentation has a maintenance cost.
Documentation is not an excuse to write code that is hard to understand.
Docstrings can include code examples, but longer one should be written to [docs].

[docs]: https://mrthearman.github.io/undine/

### All code should be linted using the projects lint rules

Easiest way to do this is to install the [pre-commit] hooks with `just hook`. This will make
sure the pre-commit hooks will run automatically when you make a commit. You can also run
hooks manually with `just lint`.

[pre-commit]: https://pre-commit.com/

Comments that ignore linting rules (`# type: ignore[...]`, `# fmt: off`, `# noqa: ...`)
should be used _**very**_ sparingly. They are often not necessary and can lead to
undocumented behavior if you are not careful.

## Guidelines for writing documentation

- All documentation is written in `docs/` using markdown, and built with [mkdocs]
- Write in idiomatic english, using simple language
- Keep examples simple and self-contained
- Give the reader time to understand the basics before going over edge cases and configurations
- Use markdown features, like [fenced code blocks], [blockquotes], [horizontal rules],
  or [links], to emphasize and format text
- If diagrams are needed, use [mermaid.js] inside [fenced code blocks]
- Break up lines around the 100 character mark
- Do not use emojis
- Double-check for spelling mistakes and grammar

[mkdocs]: https://www.mkdocs.org/
[fenced code blocks]: https://www.mkdocs.org/user-guide/writing-your-docs/#fenced-code-blocks
[blockquotes]: https://www.markdownguide.org/basic-syntax#blockquotes-1
[horizontal rules]: https://www.markdownguide.org/basic-syntax#horizontal-rules
[links]: https://www.markdownguide.org/basic-syntax#links
[mermaid.js]: https://mermaid.js.org/

## License

By contributing, you agree that your contributions will be licensed under the [MIT Licence].

[MIT Licence]: http://choosealicense.com/licenses/mit/
