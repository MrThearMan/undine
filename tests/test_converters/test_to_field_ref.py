from typing import TypedDict

from django.db.models import Subquery
from django.db.models.functions import Now

from example_project.app.models import Comment, Project, Task
from undine import Field, QueryType
from undine.converters import convert_to_field_ref
from undine.dataclasses import Calculated, LazyLambdaQueryType, LazyQueryType, LazyQueryTypeUnion


def test_convert_to_field_ref__str():
    class TaskType(QueryType, model=Task):
        name = Field("name")

    field = Task._meta.get_field("name")
    assert convert_to_field_ref("name", caller=TaskType.name) == field


def test_convert_to_field_ref__self():
    class TaskType(QueryType, model=Task):
        related_tasks = Field("self")

    assert convert_to_field_ref("self", caller=TaskType.related_tasks) == TaskType


def test_convert_to_field_ref__none():
    class TaskType(QueryType, model=Task):
        name = Field()

    field = Task._meta.get_field("name")
    assert convert_to_field_ref(None, caller=TaskType.name) == field


def test_convert_to_field_ref__function():
    def func() -> str: ...

    class TaskType(QueryType, model=Task):
        custom = Field(func)

    assert convert_to_field_ref(func, caller=TaskType.custom) == func


def test_convert_to_field_ref__lambda():
    class TaskType(QueryType, model=Task):
        custom = Field(lambda: ProjectType)

    class ProjectType(QueryType, model=Project): ...

    value = convert_to_field_ref(lambda: ProjectType, caller=TaskType.custom)

    assert isinstance(value, LazyLambdaQueryType)
    assert value.callback() == ProjectType


def test_convert_to_field_ref__expression():
    expr = Now()

    class TaskType(QueryType, model=Task):
        custom = Field(expr)

    assert convert_to_field_ref(expr, caller=TaskType.custom) == expr


def test_convert_to_field_ref__subquery():
    sq = Subquery(Task.objects.values("id"))

    class TaskType(QueryType, model=Task):
        custom = Field(sq)

    assert convert_to_field_ref(sq, caller=TaskType.custom) == sq


def test_convert_to_field_ref__model_field():
    field = Task._meta.get_field("name")

    class TaskType(QueryType, model=Task):
        name = Field(field)

    assert convert_to_field_ref(field, caller=TaskType.name) == field


def test_convert_to_field_ref__related_field():
    field = Task._meta.get_field("project")

    class TaskType(QueryType, model=Task):
        project = Field(field)

    assert convert_to_field_ref(field, caller=TaskType.project) == LazyQueryType(field=field)


def test_convert_to_field_ref__deferred_attribute():
    class TaskType(QueryType, model=Task):
        name = Field(Task.name)

    field = Task._meta.get_field("name")
    assert convert_to_field_ref(Task.name, caller=TaskType.name) == field


def test_convert_to_field_ref__forward_many_to_one_descriptor():
    class TaskType(QueryType, model=Task):
        project = Field(Task.project)

    field = Task._meta.get_field("project")
    assert convert_to_field_ref(Task.project, caller=TaskType.project) == LazyQueryType(field=field)


def test_convert_to_field_ref__reverse_many_to_one_descriptor():
    class TaskType(QueryType, model=Task):
        steps = Field(Task.steps)

    field = Task._meta.get_field("steps")
    assert convert_to_field_ref(Task.steps, caller=TaskType.steps) == LazyQueryType(field=field)


def test_convert_to_field_ref__reverse_one_to_one_descriptor():
    class TaskType(QueryType, model=Task):
        result = Field(Task.result)

    field = Task._meta.get_field("result")
    assert convert_to_field_ref(Task.result, caller=TaskType.result) == LazyQueryType(field=field)


def test_convert_to_field_ref__many_to_many_descriptor__forward():
    class TaskType(QueryType, model=Task):
        assignees = Field(Task.assignees)

    field = Task._meta.get_field("assignees")
    assert convert_to_field_ref(Task.assignees, caller=TaskType.assignees) == LazyQueryType(field=field)


def test_convert_to_field_ref__many_to_many_descriptor__reverse():
    class TaskType(QueryType, model=Task):
        reports = Field(Task.reports)

    field = Task._meta.get_field("reports")
    assert convert_to_field_ref(Task.reports, caller=TaskType.reports) == LazyQueryType(field=field)


def test_convert_to_field_ref__query_type():
    class ProjectType(QueryType, model=Project): ...

    class TaskType(QueryType, model=Task):
        project = Field(ProjectType)

    assert convert_to_field_ref(ProjectType, caller=TaskType.project) == ProjectType


def test_convert_to_field_ref__generic_relation():
    field = Task._meta.get_field("comments")

    class TaskType(QueryType, model=Task):
        comments = Field(field)

    assert convert_to_field_ref(field, caller=TaskType.comments) == LazyQueryType(field)


def test_convert_to_field_ref__generic_rel():
    class TaskType(QueryType, model=Task):
        comments = Field(Task.comments)

    field = Task._meta.get_field("comments")
    assert convert_to_field_ref(Task.comments, caller=TaskType.comments) == LazyQueryType(field)


def test_convert_to_field_ref__generic_foreign_key():
    field = Comment._meta.get_field("target")

    class CommentType(QueryType, model=Comment):
        target = Field(field)

    assert convert_to_field_ref(field, caller=CommentType.target) == LazyQueryTypeUnion(field)


def test_convert_to_field_ref__generic_foreign_key__direct_ref():
    class CommentType(QueryType, model=Comment):
        target = Field(Comment.target)

    field = Comment._meta.get_field("target")
    assert convert_to_field_ref(Comment.target, caller=CommentType.target) == LazyQueryTypeUnion(field)


def test_convert_to_field_ref__calculated():
    class Arguments(TypedDict):
        value: int

    calc = Calculated(Arguments, returns=int)

    class TaskType(QueryType, model=Task):
        name = Field(calc)

    assert convert_to_field_ref(calc, caller=TaskType.name) == calc
