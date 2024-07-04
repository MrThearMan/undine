import pytest

from example_project.app.models import Project, Task, Team
from undine.parsers import parse_model_field

pytestmark = [
    pytest.mark.django_db,
]


def test_parse_model_field__same_model():
    field = parse_model_field(model=Project, lookup="name")
    assert field == Project.name.field


def test_parse_model_field__related_model():
    field = parse_model_field(model=Project, lookup="team__name")
    assert field == Team.name.field


def test_parse_model_field__deep_related_model():
    field = parse_model_field(model=Task, lookup="project__team__name")
    assert field == Team.name.field


def test_parse_model_field__pk():
    field = parse_model_field(model=Project, lookup="pk")
    assert field == Project.id.field


def test_parse_model_field__related_model_pk():
    field = parse_model_field(model=Project, lookup="team__pk")
    assert field == Team.id.field
