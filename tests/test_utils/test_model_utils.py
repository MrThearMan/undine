import pytest

from example_project.app.models import AcceptanceCriteria, Comment, Project, Task, Team
from tests.factories import ProjectFactory
from undine.errors.exceptions import (
    GraphQLModelNotFoundError,
    GraphQLMultipleObjectsFoundError,
    ModelFieldDoesNotExistError,
    ModelFieldNotARelationError,
)
from undine.utils.model_utils import (
    generic_foreign_key_for_generic_relation,
    generic_relations_for_generic_foreign_key,
    get_instance_or_raise,
    get_lookup_field_name,
    get_model_field,
)

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


def test_get_model_field__field_doesnt_exist():
    with pytest.raises(ModelFieldDoesNotExistError):
        get_model_field(model=Project, lookup="foo")


def test_get_model_field__no_lookup():
    with pytest.raises(ModelFieldDoesNotExistError):
        get_model_field(model=Project, lookup="")


def test_get_model_field__not_a_relation():
    with pytest.raises(ModelFieldNotARelationError):
        get_model_field(model=Project, lookup="id__name")


def test_get_model_field__default_related_name():
    # Default related name for reverse foreign key and many-to-many relations contains "_set" suffix,
    # but not when asked from model meta fields.
    field = get_model_field(model=Task, lookup="acceptancecriteria_set__details")
    assert field == AcceptanceCriteria._meta.get_field("details")


def test_get_model_field__not_default_related_name():
    # If related name is overriden, then removing the "_set" suffix doesn't work.
    with pytest.raises(ModelFieldDoesNotExistError):
        get_model_field(model=Task, lookup="taskstep_set__name")


@pytest.mark.django_db
def test_get_instance_or_raise():
    project = ProjectFactory.create()

    instance = get_instance_or_raise(model=Project, key="pk", value=project.pk)
    assert instance == project


@pytest.mark.django_db
def test_get_instance_or_raise__missing():
    with pytest.raises(GraphQLModelNotFoundError):
        get_instance_or_raise(model=Project, key="pk", value=1)


@pytest.mark.django_db
def test_get_instance_or_raise__multiple():
    ProjectFactory.create(name="1")
    ProjectFactory.create(name="1")

    with pytest.raises(GraphQLMultipleObjectsFoundError):
        get_instance_or_raise(model=Project, key="name", value="1")


def test_get_lookup_field_name():
    assert get_lookup_field_name(Project) == "pk"


def test_get_lookup_field_name__no_pk(undine_settings):
    undine_settings.USE_PK_FIELD_NAME = False
    assert get_lookup_field_name(Project) == "id"


def test_generic_relations_for_generic_foreign_key():
    field = Comment._meta.get_field("target")
    relations = list(generic_relations_for_generic_foreign_key(field))

    assert relations == [
        Project._meta.get_field("comments"),
        Task._meta.get_field("comments"),
    ]


def test_generic_foreign_key_for_generic_relation():
    field = Project._meta.get_field("comments")
    generic = generic_foreign_key_for_generic_relation(field)

    assert generic == Comment._meta.get_field("target")


# TODO: Test `get_model_fields_for_graphql
