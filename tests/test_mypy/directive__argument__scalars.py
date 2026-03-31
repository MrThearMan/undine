"""
### mypy_config
[mypy]
plugins = mypy_django_plugin.main, mypy_undine

[mypy.plugins.django-stubs]
django_settings_module = example_project.project.settings

### out
main:27: error: Argument "one" to "TestDirective" has incompatible type "int"; expected "str"  [arg-type]
main:27: error: Argument "two" to "TestDirective" has incompatible type "int"; expected "str | None"  [arg-type]
"""

from graphql import GraphQLNonNull, GraphQLString

from example_project.app import models
from undine.directives import Directive, DirectiveArgument, DirectiveLocation
from undine.query import QueryType


class TestDirective(Directive, locations=[DirectiveLocation.OBJECT]):
    one = DirectiveArgument(GraphQLNonNull(GraphQLString))
    two = DirectiveArgument(GraphQLString)


@TestDirective(one=1, two=1)
class TaskType(QueryType[models.Task]): ...
