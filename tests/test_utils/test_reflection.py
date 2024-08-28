from example_project.app.models import Comment, Project, Task
from undine.utils.reflection import (
    generic_foreign_key_for_generic_relation,
    generic_relations_for_generic_foreign_key,
    swappable_by_subclassing,
)


def test_generic_relations_for_generic_foreign_key():
    gfk = Comment._meta.get_field("target")
    result_1 = Project._meta.get_field("comments")
    result_2 = Task._meta.get_field("comments")
    assert list(generic_relations_for_generic_foreign_key(gfk)) == [result_1, result_2]


def test_generic_foreign_key_for_generic_relation():
    gr = Task._meta.get_field("comments")
    result = Comment._meta.get_field("target")
    assert generic_foreign_key_for_generic_relation(gr) == result


def test_swappable_by_subclassing():
    @swappable_by_subclassing
    class A:
        def __init__(self, arg: int = 1) -> None:
            self.one = arg

    a = A()
    assert type(a) is A
    assert a.one == 1

    class B(A):
        def __init__(self, arg: int = 1) -> None:
            super().__init__(arg)
            self.two = arg * 2

    b = A(2)
    assert type(b) is B
    assert b.one == 2
    assert b.two == 4

    class C(A):
        def __init__(self, arg: int = 1, second_arg: int = 2) -> None:
            super().__init__(arg)
            self.three = second_arg * 3

    c = A(3, 4)
    assert type(c) is C
    assert c.one == 3
    assert not hasattr(c, "two")
    assert c.three == 12

    class D(B): ...

    d = A()
    assert type(d) is C  # Only direct subclasses are swapped.
