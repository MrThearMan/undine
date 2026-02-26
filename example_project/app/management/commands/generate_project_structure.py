from __future__ import annotations

import dataclasses
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional, TypeAlias

from django.conf import settings
from django.core.management import BaseCommand, CommandError

if TYPE_CHECKING:
    from django.core.management import CommandParser


class Command(BaseCommand):
    help = "Generate project structure in markdown."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "directory",
            nargs="?",
            default=settings.BASE_DIR.parent,
            help=(
                "Directory to generate the structure for. "
                "Should be a subdirectory of the project root. "
                "Default is the project root."
            ),
        )
        parser.add_argument(
            "--ignore",
            action="append",
            default=[],
            help=(
                "Additional files and directories to ignore matching the given glob pattern. "
                "By default, all files ignored by git are ignored. Can use multiple times."
            ),
        )

    def handle(self, *args: Any, **options: Any) -> None:
        base_dir = settings.BASE_DIR.parent.absolute()
        directory = Path(options["directory"]).absolute()

        if not directory.is_relative_to(base_dir):
            msg = f"Directory '{directory}' is not a subdirectory of '{base_dir}'"
            raise CommandError(msg)

        ignored = get_ignored_files()
        ignored.add(".git/")
        ignored.update(options["ignore"])

        structure = generate_folder_structure(directory=directory, ignore=ignored)
        structure = {f"{directory.name}/": structure}

        md = generate_markdown(structure)
        self.stdout.write(md)


DirectoryStructure: TypeAlias = dict[str, Optional["DirectoryStructure"]]


def get_ignored_files() -> set[str]:
    result = run_command("git status --ignored --short")
    if result.exit_code != 0:
        raise CommandError(result.err)

    ignored = [item.removeprefix("!!").strip() for item in result.out.splitlines() if item.startswith("!!")]
    return set(ignored)


def dir_sorter(entry: Path) -> tuple[bool, str]:
    return not entry.is_dir(), entry.name


def generate_folder_structure(*, directory: Path, ignore: set[str]) -> DirectoryStructure:
    markdown: DirectoryStructure = {}

    for entry in sorted(directory.iterdir(), key=dir_sorter):
        path = entry.absolute().relative_to(Path.cwd())
        str_path = str(path)
        if path.is_dir():
            str_path += "/"

        if str_path in ignore:
            continue

        if entry.name == "__init__.py":
            continue

        if entry.is_dir():
            markdown[f"{entry.name}/"] = generate_folder_structure(directory=entry.resolve(), ignore=ignore)

        elif entry.is_file():
            markdown[entry.name] = None

    return markdown


def generate_markdown(structure: DirectoryStructure, *, prefix: str = "", level: int = 0) -> str:
    markdown: str = ""

    if level == 0:
        indent = ""
        indent_last = ""
    else:
        indent = f"{prefix}├── "
        indent_last = f"{prefix}└── "

    last = len(structure) - 1
    for num, (key, value) in enumerate(structure.items()):
        if num == last:
            markdown += f"{indent_last}{key}\n"
        else:
            markdown += f"{indent}{key}\n"

        if value is not None:
            if level == 0:
                new_prefix = ""
            elif num == last:
                new_prefix = f"{prefix}    "
            else:
                new_prefix = f"{prefix}│   "

            markdown += generate_markdown(value, prefix=new_prefix, level=level + 1)

    return markdown


@dataclasses.dataclass
class CommandResult:
    out: str | None
    err: str | None
    exit_code: int


def run_command(command: str, *, directory: Path | str | None = None) -> CommandResult:
    process = subprocess.Popen(command.split(" "), stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=directory)  # noqa: S603
    stdout, stderr = process.communicate()

    error = stderr.decode().strip() or None
    result = stdout.decode().strip() if not error else None

    return CommandResult(out=result, err=error, exit_code=process.returncode)
