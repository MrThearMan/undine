import pytest

from example_project.app.models import Project, Task, Team
from undine.utils.model_utils import get_model_field

pytestmark = [
    pytest.mark.django_db,
]


def test_get_model_field__same_model():
    field = get_model_field(model=Project, lookup="name")
    assert field == Project._meta.get_field("name")


def test_get_model_field__related_model():
    field = get_model_field(model=Project, lookup="team__name")
    assert field == Team._meta.get_field("name")


def test_get_model_field__deep_related_model():
    field = get_model_field(model=Task, lookup="project__team__name")
    assert field == Team._meta.get_field("name")


def test_get_model_field__pk():
    field = get_model_field(model=Project, lookup="pk")
    assert field == Project._meta.get_field("id")


def test_get_model_field__related_model_pk():
    field = get_model_field(model=Project, lookup="team__pk")
    assert field == Team._meta.get_field("id")
