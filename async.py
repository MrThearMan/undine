from __future__ import annotations

import os

import uvicorn

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "example_project.project.settings")
    uvicorn.run("example_project.project.asgi:application", host="localhost", port=8000, reload=True)
