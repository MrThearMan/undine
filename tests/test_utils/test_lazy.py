from undine.utils.lazy import lazy


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
