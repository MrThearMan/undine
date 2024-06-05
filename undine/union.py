from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar, Generic, Unpack

from django.db.models import Model
from graphql import DirectiveLocation

from undine.exceptions import (
    GraphQLUnionResolveTypeInvalidValueError,
    GraphQLUnionResolveTypeModelNotFoundError,
    MissingUnionQueryTypeGenericError,
)
from undine.parsers import parse_class_attribute_docstrings
from undine.settings import undine_settings
from undine.typing import TQueryTypes
from undine.utils.graphql.type_registry import get_or_create_graphql_union
from undine.utils.graphql.utils import check_directives
from undine.utils.text import get_docstring

if TYPE_CHECKING:
    from collections.abc import Iterable

    from graphql import GraphQLAbstractType, GraphQLUnionType

    from undine import GQLInfo, QueryType
    from undine.directives import Directive
    from undine.typing import UnionTypeParams

__all__ = [
    "UnionType",
]


class UnionTypeMeta(type):
    """A metaclass that modifies how a `UnionType` is created."""

    # Set in '__new__'
    __query_types_by_model__: dict[type[Model], type[QueryType]]
    __schema_name__: str
    __directives__: list[Directive]
    __extensions__: dict[str, Any]
    __attribute_docstrings__: dict[str, str]

    # Internal use only
    __query_types__: Iterable[type[QueryType]]

    def __new__(
        cls,
        _name: str,
        _bases: tuple[type, ...],
        _attrs: dict[str, Any],
        **kwargs: Unpack[UnionTypeParams],
    ) -> UnionTypeMeta:
        if _name == "UnionType":  # Early return for the `UnionType` class itself.
            return super().__new__(cls, _name, _bases, _attrs)

        try:
            query_types = UnionTypeMeta.__query_types__
            del UnionTypeMeta.__query_types__
        except AttributeError as error:
            raise MissingUnionQueryTypeGenericError(name=_name, cls="UnionType") from error

        union_type = super().__new__(cls, _name, _bases, _attrs)

        union_type.__query_types_by_model__ = {query_type.__model__: query_type for query_type in query_types}
        union_type.__schema_name__ = kwargs.get("schema_name", _name)
        union_type.__directives__ = kwargs.get("directives", [])
        union_type.__extensions__ = kwargs.get("extensions", {})
        union_type.__attribute_docstrings__ = parse_class_attribute_docstrings(union_type)

        check_directives(union_type.__directives__, location=DirectiveLocation.UNION)
        union_type.__extensions__[undine_settings.UNION_TYPE_EXTENSIONS_KEY] = union_type

        return union_type

    def __str__(cls) -> str:
        return undine_settings.SDL_PRINTER.print_union_type(cls.__union_type__())

    def __getitem__(cls, query_types: tuple[type[QueryType], ...]) -> type[UnionType[*TQueryTypes]]:
        # Note that this should be cleaned up in '__new__',
        # but is not if an error occurs in the class body of the defined 'UnionType'!
        UnionTypeMeta.__query_types__ = query_types
        return cls  # type: ignore[return-value]

    def __resolve_type__(cls, value: Any, info: GQLInfo, abstract_type: GraphQLAbstractType) -> str:
        if not isinstance(value, Model):
            raise GraphQLUnionResolveTypeInvalidValueError(name=cls.__schema_name__, value=value)

        model = value.__class__
        query_type = cls.__query_types_by_model__.get(model)
        if query_type is None:
            raise GraphQLUnionResolveTypeModelNotFoundError(name=cls.__schema_name__, model=model)

        return query_type.__schema_name__

    def __union_type__(cls) -> GraphQLUnionType:
        return get_or_create_graphql_union(
            name=cls.__schema_name__,
            types=[query_type.__output_type__() for query_type in cls.__query_types_by_model__.values()],
            resolve_type=cls.__resolve_type__,
            description=get_docstring(cls),
            extensions=cls.__extensions__,
        )


class UnionType(Generic[*TQueryTypes], metaclass=UnionTypeMeta):
    """
    A class for creating a GraphQL Union based on two or more `QueryTypes`.

    Must set the `QueryTypes` this `UnionType` contains using the generic type argument.

    The following parameters can be passed in the class definition:

    `schema_name: str = <class name>`
        Override name for `UnionType` in the GraphQL schema.

    `directives: list[Directive] = []`
        `Directives` to add to the created `UnionType`.

    `extensions: dict[str, Any] = {}`
        GraphQL extensions for the created `UnionType`.

    >>> class TaskType(QueryType[Task]): ...
    >>> class ProjectType(QueryType[Project]): ...
    >>>
    >>> class Commentable(UnionType[TaskType, ProjectType]): ...
    """

    # Set in metaclass
    __query_types_by_model__: ClassVar[dict[type[Model], type[QueryType]]]
    __schema_name__: ClassVar[str]
    __directives__: ClassVar[list[Directive]]
    __extensions__: ClassVar[dict[str, Any]]
    __attribute_docstrings__: ClassVar[dict[str, str]]

    @classmethod
    def __process_results__(cls, instances: list[Any], info: GQLInfo) -> list[Any]:
        """Filter and order results of the union after everything has been fetched."""
        return instances
