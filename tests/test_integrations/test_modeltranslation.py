from __future__ import annotations

from django.db.models import CharField, Model
from graphql import GraphQLNonNull, GraphQLString
from modeltranslation.decorators import register
from modeltranslation.translator import TranslationOptions

from undine import FilterSet, MutationType, OrderSet, QueryType


class TestModel(Model):
    name = CharField(max_length=255)

    class Meta:
        managed = False
        app_label = __name__

    def __str__(self) -> str:
        return self.name


@register(TestModel)
class TestModelOptions(TranslationOptions):
    fields = ["name"]


def test_modeltranslation__query_type_fields__include_translatable_and_translations(undine_settings) -> None:
    undine_settings.MODELTRANSLATION_INCLUDE_TRANSLATABLE = True
    undine_settings.MODELTRANSLATION_INCLUDE_TRANSLATIONS = True

    class TranslatedType(QueryType[TestModel], exclude=["pk"]): ...

    fields = TranslatedType.__field_map__
    assert sorted(fields) == ["name", "name_en", "name_fi"]

    name_en_field = fields["name"].as_graphql_field()
    assert name_en_field.type == GraphQLNonNull(GraphQLString)

    name_en_field = fields["name_en"].as_graphql_field()
    assert name_en_field.type == GraphQLString

    name_fi_field = fields["name_fi"].as_graphql_field()
    assert name_fi_field.type == GraphQLString


def test_modeltranslation__query_type_fields__only_translatable(undine_settings) -> None:
    undine_settings.MODELTRANSLATION_INCLUDE_TRANSLATABLE = True
    undine_settings.MODELTRANSLATION_INCLUDE_TRANSLATIONS = False

    class TranslatedType(QueryType[TestModel], exclude=["pk"]): ...

    fields = TranslatedType.__field_map__
    assert sorted(fields) == ["name"]

    name_en_field = fields["name"].as_graphql_field()
    assert name_en_field.type == GraphQLNonNull(GraphQLString)


def test_modeltranslation__query_type_fields__only_translations(undine_settings) -> None:
    undine_settings.MODELTRANSLATION_INCLUDE_TRANSLATABLE = False
    undine_settings.MODELTRANSLATION_INCLUDE_TRANSLATIONS = True

    class TranslatedType(QueryType[TestModel], exclude=["pk"]): ...

    fields = TranslatedType.__field_map__
    assert sorted(fields) == ["name_en", "name_fi"]

    name_en_field = fields["name_en"].as_graphql_field()
    assert name_en_field.type == GraphQLString

    name_fi_field = fields["name_fi"].as_graphql_field()
    assert name_fi_field.type == GraphQLString


def test_modeltranslation__mutation_inputs__include_translatable_and_translations(undine_settings) -> None:
    undine_settings.MODELTRANSLATION_INCLUDE_TRANSLATABLE = True
    undine_settings.MODELTRANSLATION_INCLUDE_TRANSLATIONS = True

    class TranslationCreateMutation(MutationType[TestModel]): ...

    inputs = TranslationCreateMutation.__input_map__
    assert sorted(inputs) == ["name", "name_en", "name_fi"]

    name_en_field = inputs["name"].as_graphql_input_field()
    assert name_en_field.type == GraphQLNonNull(GraphQLString)

    name_en_field = inputs["name_en"].as_graphql_input_field()
    assert name_en_field.type == GraphQLString

    name_fi_field = inputs["name_fi"].as_graphql_input_field()
    assert name_fi_field.type == GraphQLString


def test_modeltranslation__mutation_inputs__only_translatable(undine_settings) -> None:
    undine_settings.MODELTRANSLATION_INCLUDE_TRANSLATABLE = True
    undine_settings.MODELTRANSLATION_INCLUDE_TRANSLATIONS = False

    class TranslationCreateMutation(MutationType[TestModel]): ...

    inputs = TranslationCreateMutation.__input_map__
    assert sorted(inputs) == ["name"]

    name_en_field = inputs["name"].as_graphql_input_field()
    assert name_en_field.type == GraphQLNonNull(GraphQLString)


def test_modeltranslation__mutation_inputs__only_translations(undine_settings) -> None:
    undine_settings.MODELTRANSLATION_INCLUDE_TRANSLATABLE = False
    undine_settings.MODELTRANSLATION_INCLUDE_TRANSLATIONS = True

    class TranslationCreateMutation(MutationType[TestModel]): ...

    inputs = TranslationCreateMutation.__input_map__
    assert sorted(inputs) == ["name_en", "name_fi"]

    name_en_field = inputs["name_en"].as_graphql_input_field()
    assert name_en_field.type == GraphQLString

    name_fi_field = inputs["name_fi"].as_graphql_input_field()
    assert name_fi_field.type == GraphQLString


def test_modeltranslation__filterset_filters__include_translatable_and_translations(undine_settings) -> None:
    undine_settings.MODELTRANSLATION_INCLUDE_TRANSLATABLE = True
    undine_settings.MODELTRANSLATION_INCLUDE_TRANSLATIONS = True

    class TranslationFilterSet(FilterSet[TestModel], exclude=["pk"]): ...

    filters = TranslationFilterSet.__filter_map__
    assert sorted(filters) == [
        "name",
        "name_contains",
        "name_contains_exact",
        "name_en",
        "name_en_contains",
        "name_en_contains_exact",
        "name_en_ends_with",
        "name_en_ends_with_exact",
        "name_en_exact",
        "name_en_in",
        "name_en_is_null",
        "name_en_starts_with",
        "name_en_starts_with_exact",
        "name_ends_with",
        "name_ends_with_exact",
        "name_exact",
        "name_fi",
        "name_fi_contains",
        "name_fi_contains_exact",
        "name_fi_ends_with",
        "name_fi_ends_with_exact",
        "name_fi_exact",
        "name_fi_in",
        "name_fi_is_null",
        "name_fi_starts_with",
        "name_fi_starts_with_exact",
        "name_in",
        "name_starts_with",
        "name_starts_with_exact",
    ]


def test_modeltranslation__filterset_filters__only_translatable(undine_settings) -> None:
    undine_settings.MODELTRANSLATION_INCLUDE_TRANSLATABLE = True
    undine_settings.MODELTRANSLATION_INCLUDE_TRANSLATIONS = False

    class TranslationFilterSet(FilterSet[TestModel], exclude=["pk"]): ...

    filters = TranslationFilterSet.__filter_map__
    assert sorted(filters) == [
        "name",
        "name_contains",
        "name_contains_exact",
        "name_ends_with",
        "name_ends_with_exact",
        "name_exact",
        "name_in",
        "name_starts_with",
        "name_starts_with_exact",
    ]


def test_modeltranslation__filterset_filters__only_translations(undine_settings) -> None:
    undine_settings.MODELTRANSLATION_INCLUDE_TRANSLATABLE = False
    undine_settings.MODELTRANSLATION_INCLUDE_TRANSLATIONS = True

    class TranslationFilterSet(FilterSet[TestModel], exclude=["pk"]): ...

    filters = TranslationFilterSet.__filter_map__
    assert sorted(filters) == [
        "name_en",
        "name_en_contains",
        "name_en_contains_exact",
        "name_en_ends_with",
        "name_en_ends_with_exact",
        "name_en_exact",
        "name_en_in",
        "name_en_is_null",
        "name_en_starts_with",
        "name_en_starts_with_exact",
        "name_fi",
        "name_fi_contains",
        "name_fi_contains_exact",
        "name_fi_ends_with",
        "name_fi_ends_with_exact",
        "name_fi_exact",
        "name_fi_in",
        "name_fi_is_null",
        "name_fi_starts_with",
        "name_fi_starts_with_exact",
    ]


def test_modeltranslation__orderset_orders__include_translatable_and_translations(undine_settings) -> None:
    undine_settings.MODELTRANSLATION_INCLUDE_TRANSLATABLE = True
    undine_settings.MODELTRANSLATION_INCLUDE_TRANSLATIONS = True

    class TranslationOrderSet(OrderSet[TestModel], exclude=["pk"]): ...

    orders = TranslationOrderSet.__order_map__
    assert sorted(orders) == ["name", "name_en", "name_fi"]


def test_modeltranslation__orderset_orders__only_translatable(undine_settings) -> None:
    undine_settings.MODELTRANSLATION_INCLUDE_TRANSLATABLE = True
    undine_settings.MODELTRANSLATION_INCLUDE_TRANSLATIONS = False

    class TranslationOrderSet(OrderSet[TestModel], exclude=["pk"]): ...

    orders = TranslationOrderSet.__order_map__
    assert sorted(orders) == ["name"]


def test_modeltranslation__orderset_orders__only_translations(undine_settings) -> None:
    undine_settings.MODELTRANSLATION_INCLUDE_TRANSLATABLE = False
    undine_settings.MODELTRANSLATION_INCLUDE_TRANSLATIONS = True

    class TranslationOrderSet(OrderSet[TestModel], exclude=["pk"]): ...

    orders = TranslationOrderSet.__order_map__
    assert sorted(orders) == ["name_en", "name_fi"]
