from __future__ import annotations

import os
import sys
from pathlib import Path


def main() -> None:
    base_dir = str(Path(__file__).resolve().parent)
    if base_dir not in sys.path:
        sys.path.insert(0, base_dir)

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

    from django.core.management import execute_from_command_line  # noqa: PLC0415

    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
