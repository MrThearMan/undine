import pytest

from tests.example.models import Project, Task, Team
from undine.parsers import parse_model_field

pytestmark = [
    pytest.mark.django_db,
]


def test_parse_model_field__same_model():
    field = parse_model_field(Project, "name")
    assert field == Project.name.field


def test_parse_model_field__related_model():
    field = parse_model_field(Project, "team__name")
    assert field == Team.name.field


def test_parse_model_field__deep_related_model():
    field = parse_model_field(Task, "project__team__name")
    assert field == Team.name.field


def test_parse_model_field__pk():
    field = parse_model_field(Project, "pk")
    assert field == Project.id.field


def test_parse_model_field__related_model_pk():
    field = parse_model_field(Project, "team__pk")
    assert field == Team.id.field
