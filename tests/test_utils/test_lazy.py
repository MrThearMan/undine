from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.db import models

from example_project.app.models import Comment, Person, Project, Report, ServiceRequest, Task, TaskResult, TaskStep
from undine import QueryType
from undine.utils.lazy import LazyQueryType, LazyQueryTypeUnion, lazy


def test_lazy():
    foo: str = "1"

    def func():
        nonlocal foo
        foo += "1"
        return foo

    ret = lazy.create(func)

    # Accessing the original object before the lazy object
    # Original has not changed.
    assert foo == "1"

    # Accessig the lazy object should evaluate the target
    assert ret == "11"
    assert foo == "11"

    # Accessing the lazy object should not evaluate the target again
    assert ret == "11"
    assert foo == "11"


def test_lazy_model_gql_type__forward_one_to_one():
    class ServiceRequestType(QueryType, model=ServiceRequest): ...

    field = Task._meta.get_field("request")
    assert isinstance(field, models.OneToOneField)

    lazy_type = LazyQueryType(field=field)
    gql_type = lazy_type.get_type()
    assert gql_type == ServiceRequestType


def test_lazy_model_gql_type__forward_many_to_one():
    class ProjectType(QueryType, model=Project): ...

    field = Task._meta.get_field("project")
    assert isinstance(field, models.ForeignKey)

    lazy_type = LazyQueryType(field=field)
    gql_type = lazy_type.get_type()
    assert gql_type == ProjectType


def test_lazy_model_gql_type__forward_many_to_many():
    class PersonType(QueryType, model=Person): ...

    field = Task._meta.get_field("assignees")
    assert isinstance(field, models.ManyToManyField)

    lazy_type = LazyQueryType(field=field)
    gql_type = lazy_type.get_type()
    assert gql_type == PersonType


def test_lazy_model_gql_type__forward_many_to_many__self():
    class TaskType(QueryType, model=Task): ...

    field = Task._meta.get_field("related_tasks")
    assert isinstance(field, models.ManyToManyField)

    lazy_type = LazyQueryType(field=field)
    gql_type = lazy_type.get_type()
    assert gql_type == TaskType


def test_lazy_model_gql_type__reverse_one_to_one():
    class TaskResultType(QueryType, model=TaskResult): ...

    field = Task._meta.get_field("result")
    assert isinstance(field, models.OneToOneRel)

    lazy_type = LazyQueryType(field=field)
    gql_type = lazy_type.get_type()
    assert gql_type == TaskResultType


def test_lazy_model_gql_type__reverse_one_to_many():
    class TaskStepType(QueryType, model=TaskStep): ...

    field = Task._meta.get_field("steps")
    assert isinstance(field, models.ManyToOneRel)

    lazy_type = LazyQueryType(field=field)
    gql_type = lazy_type.get_type()
    assert gql_type == TaskStepType


def test_lazy_model_gql_type__reverse_many_to_many():
    class ReportType(QueryType, model=Report): ...

    field = Task._meta.get_field("reports")
    assert isinstance(field, models.ManyToManyRel)

    lazy_type = LazyQueryType(field=field)
    gql_type = lazy_type.get_type()
    assert gql_type == ReportType


def test_lazy_model_gql_type__generic_relation():
    class CommentType(QueryType, model=Comment): ...

    field = Task._meta.get_field("comments")
    assert isinstance(field, GenericRelation)

    lazy_type = LazyQueryType(field=field)
    gql_type = lazy_type.get_type()
    assert gql_type == CommentType


def test_lazy_model_gql_type_union__generic_foreign_key():
    class ProjectType(QueryType, model=Project): ...

    class TaskType(QueryType, model=Task): ...

    field = Comment._meta.get_field("target")
    assert isinstance(field, GenericForeignKey)

    lazy_type = LazyQueryTypeUnion(field=field)
    gql_type = lazy_type.get_types()
    assert isinstance(gql_type, list)
    assert len(gql_type) == 2
    assert gql_type[0] == ProjectType
    assert gql_type[1] == TaskType
