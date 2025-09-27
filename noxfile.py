from __future__ import annotations

import logging
import re
import tomllib
from functools import cache
from pathlib import Path

import nox

logger = logging.getLogger(__name__)


@cache
def python_versions() -> list[str]:
    pyproject = Path("pyproject.toml").read_text(encoding="utf-8")
    toml_data = tomllib.loads(pyproject)
    classifiers: list[str] = toml_data["project"]["classifiers"]

    python_version_pattern = re.compile(r"^Programming Language :: Python :: (?P<version>\d+\.\d+)$")

    versions: list[str] = []
    for classifier in classifiers:
        match = python_version_pattern.match(classifier)
        if match is not None:
            versions.append(match.group("version"))

    logger.debug(f"Python versions: {', '.join(versions)}")
    return versions


@nox.session(python=python_versions(), reuse_venv=True)
@nox.parametrize("django", ["5.0.*", "5.1.*", "5.2.*", "6.0a1"])
@nox.parametrize("graphql_core", ["3.2.*", "3.3.0a9"])
def tests(session: nox.Session, django: str, graphql_core: str) -> None:
    # Django 6.0 is only supports python 3.12 and above
    if django == "6.0a1" and session.python == "3.11":
        session.skip()

    env = {
        "POETRY_VIRTUALENVS_PATH": str(Path(session.virtualenv.bin).parent),
    }

    session.run_install("poetry", "install", "--all-extras", external=True, env=env)
    session.install(f"django=={django}")
    session.install(f"graphql-core=={graphql_core}")

    session.run("coverage", "run", "-m", "pytest", external="error")


if __name__ == "__main__":
    nox.main()
