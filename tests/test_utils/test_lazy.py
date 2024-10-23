import math
from copy import copy, deepcopy
from types import SimpleNamespace

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

    # Accessing the original object before the lazy object. Original has not changed.
    assert foo == "1"

    # Accessig the lazy object should evaluate the target.
    assert ret == "11"
    assert foo == "11"

    # Accessing the lazy object again should not evaluate the target again.
    assert ret == "11"
    assert foo == "11"


def test_lazy__getattr():
    lz = lazy.create(lambda: "foo")
    assert lz.capitalize() == "Foo"


def test_lazy__setattr():
    obj = SimpleNamespace()
    lz = lazy.create(lambda: obj)
    lz.foo = "bar"
    assert obj.foo == "bar"


def test_lazy__delattr():
    obj = SimpleNamespace(foo="bar")
    lz = lazy.create(lambda: obj)
    del lz.foo
    assert not hasattr(obj, "foo")


def test_lazy__call():
    def foo():
        return "bar"

    lz = lazy.create(lambda: foo)
    assert lz() == "bar"


def test_lazy__eq():
    lz = lazy.create(lambda: "foo")
    assert lz == "foo"


def test_lazy__hash():
    lz = lazy.create(lambda: "foo")
    assert hash(lz) == hash("foo")


def test_lazy__repr():
    lz = lazy.create(lambda: "foo")
    assert repr(lz) == repr("foo")


def test_lazy__str():
    lz = lazy.create(lambda: "foo")
    assert str(lz) == str("foo")


def test_lazy__bool():
    lz = lazy.create(lambda: "foo")
    assert bool(lz) == bool("foo")


def test_lazy__bytes():
    lz = lazy.create(lambda: b"foo")
    assert bytes(lz) == bytes(b"foo")


def test_lazy__format():
    lz = lazy.create(lambda: 1.2345)
    assert format(lz, ".2f") == format(1.2345, ".2f")


def test_lazy__dir():
    lz = lazy.create(lambda: "foo")
    assert dir(lz) == dir("foo")


def test_lazy__lt():
    lz = lazy.create(lambda: 1)
    assert lz < 2


def test_lazy__le():
    lz = lazy.create(lambda: 1)
    assert lz <= 2


def test_lazy__gt():
    lz = lazy.create(lambda: 1)
    assert lz > 0


def test_lazy__ge():
    lz = lazy.create(lambda: 1)
    assert lz >= 0


def test_lazy__add():
    lz = lazy.create(lambda: 1)
    assert lz + 1 == 2


def test_lazy__sub():
    lz = lazy.create(lambda: 1)
    assert lz - 1 == 0


def test_lazy__mul():
    lz = lazy.create(lambda: 1)
    assert lz * 2 == 2


def test_lazy__truediv():
    lz = lazy.create(lambda: 2)
    assert lz / 2 == 1


def test_lazy__floordiv():
    lz = lazy.create(lambda: 5)
    assert lz // 2 == 2


def test_lazy__mod():
    lz = lazy.create(lambda: 5)
    assert lz % 2 == 1


def test_lazy__divmod():
    lz = lazy.create(lambda: 5)
    assert divmod(lz, 2) == (2, 1)


def test_lazy__pow():
    lz = lazy.create(lambda: 2)
    assert lz**2 == 4


def test_lazy__lshift():
    lz = lazy.create(lambda: 2)
    assert lz << 1 == 4


def test_lazy__rshift():
    lz = lazy.create(lambda: 4)
    assert lz >> 1 == 2


def test_lazy__and():
    lz = lazy.create(lambda: 1)
    assert lz & 1 == 1


def test_lazy__xor():
    lz = lazy.create(lambda: 1)
    assert lz ^ 1 == 0


def test_lazy__or():
    lz = lazy.create(lambda: 1)
    assert lz | 1 == 1


def test_lazy__radd():
    lz = lazy.create(lambda: 1)
    assert 1 + lz == 2


def test_lazy__rsub():
    lz = lazy.create(lambda: 1)
    assert 1 - lz == 0


def test_lazy__rmul():
    lz = lazy.create(lambda: 1)
    assert 2 * lz == 2


def test_lazy__rtruediv():
    lz = lazy.create(lambda: 2)
    assert 2 / lz == 1


def test_lazy__rfloordiv():
    lz = lazy.create(lambda: 2)
    assert 5 // lz == 2


def test_lazy__rmod():
    lz = lazy.create(lambda: 2)
    assert 5 % lz == 1


def test_lazy__rdivmod():
    lz = lazy.create(lambda: 2)
    assert divmod(5, lz) == (2, 1)


def test_lazy__neg():
    lz = lazy.create(lambda: 1)
    assert -lz == -1


def test_lazy__pos():
    lz = lazy.create(lambda: 1)
    assert +lz == +1


def test_lazy__abs():
    lz = lazy.create(lambda: 1)
    assert abs(lz) == 1


def test_lazy__invert():
    lz = lazy.create(lambda: 1)
    assert ~lz == ~1


def test_lazy__round():
    lz = lazy.create(lambda: 1.2)
    assert round(lz) == 1


def test_lazy__floor():
    lz = lazy.create(lambda: 1.2)
    assert math.floor(lz) == 1


def test_lazy__ceil():
    lz = lazy.create(lambda: 1.2)
    assert math.ceil(lz) == 2


def test_lazy__trunc():
    lz = lazy.create(lambda: 1.2)
    assert math.trunc(lz) == 1


def test_lazy__float():
    lz = lazy.create(lambda: 1.2)
    assert float(lz) == 1.2


def test_lazy__int():
    lz = lazy.create(lambda: 1.2)
    assert int(lz) == 1


def test_lazy__complex():
    lz = lazy.create(lambda: "1+2j")
    assert complex(lz) == (1 + 2j)


def test_lazy__index():
    lz = lazy.create(lambda: 1)
    assert lz.__index__() == 1


def test_lazy__len():
    lz = lazy.create(lambda: "123")
    assert len(lz) == 3


def test_lazy__getitem():
    lz = lazy.create(lambda: "123")
    assert lz[0] == "1"


def test_lazy__setitem():
    lz = lazy.create(lambda: [1, 2, 3])
    lz[0] = 10
    assert lz[0] == 10


def test_lazy__delitem():
    lz = lazy.create(lambda: [1, 2, 3])
    del lz[0]
    assert lz[0] == 2


def test_lazy__contains():
    lz = lazy.create(lambda: [1, 2, 3])
    assert 1 in lz


def test_lazy__iter():
    lz = lazy.create(lambda: [1, 2, 3])
    assert list(iter(lz)) == [1, 2, 3]


def test_lazy__reversed():
    lz = lazy.create(lambda: [1, 2, 3])
    assert list(reversed(lz)) == [3, 2, 1]


def test_lazy__next():
    lz = lazy.create(lambda: iter([1, 2, 3]))
    assert next(lz) == 1


def test_lazy__enter_and_exit():
    class Obj:
        value = 0

        def __enter__(self):
            self.value += 1
            return self

        def __exit__(self, *args, **kwargs):
            self.value += 1

    obj = Obj()

    lz = lazy.create(lambda: obj)
    with lz as foo:
        assert foo.value == 1
    assert foo.value == 2


def test_lazy__copy():
    lz = lazy.create(lambda: [1, 2, 3])
    assert copy(lz) == [1, 2, 3]


def test_lazy__deepcopy():
    lz = lazy.create(lambda: [1, 2, 3])
    assert deepcopy(lz) == [1, 2, 3]


def test_lazy__getstate():
    class Obj:
        def __getstate__(self):
            return [1, 2, 3]

    obj = Obj()

    lz = lazy.create(lambda: obj)
    assert lz.__getstate__() == [1, 2, 3]


def test_lazy__setstate():
    class Obj:
        def __setstate__(self, state):
            return state

    obj = Obj()

    lz = lazy.create(lambda: obj)
    assert lz.__setstate__(1) == 1


def test_lazy__reduce():
    class Obj:
        def __reduce__(self):
            return 1

    obj = Obj()

    lz = lazy.create(lambda: obj)
    assert lz.__reduce__() == 1


def test_lazy__reduce_ex():
    class Obj:
        def __reduce_ex__(self, protocol):
            return protocol

    obj = Obj()

    lz = lazy.create(lambda: obj)
    assert lz.__reduce_ex__(1) == 1


def test_lazy__sizeof():
    class Obj:
        def __sizeof__(self):
            return 1

    obj = Obj()

    lz = lazy.create(lambda: obj)
    assert lz.__sizeof__() == 1


def test_lazy__instancecheck():
    class Obj:
        def __instancecheck__(self, instance):
            return isinstance(instance, Obj)

    obj = Obj()

    lz = lazy.create(lambda: obj)
    assert lz.__instancecheck__(obj) is True


def test_lazy__subclasscheck():
    class Obj:
        def __subclasscheck__(self, clss):
            return issubclass(clss, Obj)

    obj = Obj()

    lz = lazy.create(lambda: obj)
    assert lz.__subclasscheck__(Obj) is True


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
