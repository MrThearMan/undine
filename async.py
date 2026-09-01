from __future__ import annotations

import os
from argparse import ArgumentParser

from granian import Granian
from granian.constants import Interfaces
from granian.log import LogLevels

if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--log-level", type=str, default="info")
    args = parser.parse_args()

    os.environ.setdefault("ASYNC", "true")
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "example_project.project.settings")
    Granian(
        target="example_project.project.asgi:application",
        port=args.port,
        interface=Interfaces.ASGI,
        log_level=LogLevels(args.log_level),
    ).serve()
