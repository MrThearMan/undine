from __future__ import annotations

import pytest

from example_project.app.models import Task
from undine import Entrypoint, Field, QueryType, RootType
from undine.exceptions import (
    FederationRequiresNonExternalFieldError,
    FederationRequiresUnknownFieldError,
)
from undine.federation import (
    ExternalDirective,
    FederationField,
    FederationType,
    KeyDirective,
    RequiresDirective,
    create_federation_schema,
)


def test_federation_field_requires__valid_external_reference_passes_and_renders_in_sdl() -> None:
    @KeyDirective(fields="isbn")
    class BookExt(FederationType, schema_name="Book"):
        isbn = FederationField(str)
        weight = FederationField(int) @ ExternalDirective()
        shipping = FederationField(int) @ RequiresDirective(fields="weight")

        @shipping.resolve
        def resolve_shipping(self, info):  # noqa: ARG002
            return 0

    class TaskType(QueryType[Task]):
        name = Field()

    class Query(RootType):
        task = Entrypoint(TaskType)

    schema = create_federation_schema(query=Query)
    sdl = schema.extensions["undine_federation_sdl"]

    assert 'shipping: Int! @requires(fields: "weight")' in sdl


def test_federation_field_requires__unknown_token_raises_at_class_definition_time() -> None:
    with pytest.raises(FederationRequiresUnknownFieldError, match="nonexistent"):

        @KeyDirective(fields="isbn")
        class BookExt(FederationType, schema_name="Book"):
            isbn = FederationField(str)
            shipping = FederationField(int) @ RequiresDirective(fields="nonexistent")

            @shipping.resolve
            def resolve_shipping(self, info):  # noqa: ARG002
                return 0


def test_federation_field_requires__non_external_token_raises_at_class_definition_time() -> None:
    with pytest.raises(FederationRequiresNonExternalFieldError, match="weight"):

        @KeyDirective(fields="isbn")
        class BookExt(FederationType, schema_name="Book"):
            isbn = FederationField(str)
            weight = FederationField(int)

            @weight.resolve
            def resolve_weight(self, info):  # noqa: ARG002
                return 0

            shipping = FederationField(int) @ RequiresDirective(fields="weight")

            @shipping.resolve
            def resolve_shipping(self, info):  # noqa: ARG002
                return 0


def test_federation_field_requires__multi_token_all_valid_passes() -> None:
    @KeyDirective(fields="isbn")
    class BookExt(FederationType, schema_name="Book"):
        isbn = FederationField(str)
        weight = FederationField(int) @ ExternalDirective()
        height = FederationField(int) @ ExternalDirective()
        shipping = FederationField(int) @ RequiresDirective(fields="weight height")

        @shipping.resolve
        def resolve_shipping(self, info):  # noqa: ARG002
            return 0

    class TaskType(QueryType[Task]):
        name = Field()

    class Query(RootType):
        task = Entrypoint(TaskType)

    schema = create_federation_schema(query=Query)
    sdl = schema.extensions["undine_federation_sdl"]

    assert 'shipping: Int! @requires(fields: "weight height")' in sdl


def test_federation_field_requires__multi_token_with_invalid_raises_on_first_bad_token() -> None:
    with pytest.raises(FederationRequiresUnknownFieldError):

        @KeyDirective(fields="isbn")
        class BookExt(FederationType, schema_name="Book"):
            isbn = FederationField(str)
            weight = FederationField(int) @ ExternalDirective()
            shipping = FederationField(int) @ RequiresDirective(fields="weight bogus")

            @shipping.resolve
            def resolve_shipping(self, info):  # noqa: ARG002
                return 0


def test_federation_field_requires__on_query_type_field_skips_validation() -> None:
    # QueryType-Field targets bypass class-definition-time validation of @requires.
    @KeyDirective(fields="pk")
    class TaskType(QueryType[Task]):
        pk = Field()
        name = Field() @ RequiresDirective(fields="anything_goes")

    class Query(RootType):
        task = Entrypoint(TaskType)

    schema = create_federation_schema(query=Query)
    sdl = schema.extensions["undine_federation_sdl"]

    assert '@requires(fields: "anything_goes")' in sdl
