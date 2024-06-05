from django import apps

__all__ = [
    "ExampleConfig",
]


class ExampleConfig(apps.AppConfig):
    name = "example_project.example"
