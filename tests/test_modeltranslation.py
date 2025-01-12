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


def test_modeltranslation__query_type_fields__include_translatable_and_translations(undine_settings):
    undine_settings.MODELTRANSLATION_INCLUDE_TRANSLATABLE = True
    undine_settings.MODELTRANSLATION_INCLUDE_TRANSLATIONS = True

    class TranslatedType(QueryType, model=TestModel, exclude=["pk"]): ...

    fields = TranslatedType.__field_map__
    assert sorted(fields) == ["name", "name_en", "name_fi"]

    name_en_field = fields["name"].as_graphql_field()
    assert name_en_field.type == GraphQLNonNull(GraphQLString)

    name_en_field = fields["name_en"].as_graphql_field()
    assert name_en_field.type == GraphQLString

    name_fi_field = fields["name_fi"].as_graphql_field()
    assert name_fi_field.type == GraphQLString


def test_modeltranslation__query_type_fields__only_translatable(undine_settings):
    undine_settings.MODELTRANSLATION_INCLUDE_TRANSLATABLE = True
    undine_settings.MODELTRANSLATION_INCLUDE_TRANSLATIONS = False

    class TranslatedType(QueryType, model=TestModel, exclude=["pk"]): ...

    fields = TranslatedType.__field_map__
    assert sorted(fields) == ["name"]

    name_en_field = fields["name"].as_graphql_field()
    assert name_en_field.type == GraphQLNonNull(GraphQLString)


def test_modeltranslation__query_type_fields__only_translations(undine_settings):
    undine_settings.MODELTRANSLATION_INCLUDE_TRANSLATABLE = False
    undine_settings.MODELTRANSLATION_INCLUDE_TRANSLATIONS = True

    class TranslatedType(QueryType, model=TestModel, exclude=["pk"]): ...

    fields = TranslatedType.__field_map__
    assert sorted(fields) == ["name_en", "name_fi"]

    name_en_field = fields["name_en"].as_graphql_field()
    assert name_en_field.type == GraphQLString

    name_fi_field = fields["name_fi"].as_graphql_field()
    assert name_fi_field.type == GraphQLString


def test_modeltranslation__mutation_inputs__include_translatable_and_translations(undine_settings):
    undine_settings.MODELTRANSLATION_INCLUDE_TRANSLATABLE = True
    undine_settings.MODELTRANSLATION_INCLUDE_TRANSLATIONS = True

    class TranslationCreateMutation(MutationType, model=TestModel): ...

    inputs = TranslationCreateMutation.__input_map__
    assert sorted(inputs) == ["name", "name_en", "name_fi"]

    name_en_field = inputs["name"].as_graphql_input_field()
    assert name_en_field.type == GraphQLNonNull(GraphQLString)

    name_en_field = inputs["name_en"].as_graphql_input_field()
    assert name_en_field.type == GraphQLString

    name_fi_field = inputs["name_fi"].as_graphql_input_field()
    assert name_fi_field.type == GraphQLString


def test_modeltranslation__mutation_inputs__only_translatable(undine_settings):
    undine_settings.MODELTRANSLATION_INCLUDE_TRANSLATABLE = True
    undine_settings.MODELTRANSLATION_INCLUDE_TRANSLATIONS = False

    class TranslationCreateMutation(MutationType, model=TestModel): ...

    inputs = TranslationCreateMutation.__input_map__
    assert sorted(inputs) == ["name"]

    name_en_field = inputs["name"].as_graphql_input_field()
    assert name_en_field.type == GraphQLNonNull(GraphQLString)


def test_modeltranslation__mutation_inputs__only_translations(undine_settings):
    undine_settings.MODELTRANSLATION_INCLUDE_TRANSLATABLE = False
    undine_settings.MODELTRANSLATION_INCLUDE_TRANSLATIONS = True

    class TranslationCreateMutation(MutationType, model=TestModel): ...

    inputs = TranslationCreateMutation.__input_map__
    assert sorted(inputs) == ["name_en", "name_fi"]

    name_en_field = inputs["name_en"].as_graphql_input_field()
    assert name_en_field.type == GraphQLString

    name_fi_field = inputs["name_fi"].as_graphql_input_field()
    assert name_fi_field.type == GraphQLString


def test_modeltranslation__filterset_filters__include_translatable_and_translations(undine_settings):
    undine_settings.MODELTRANSLATION_INCLUDE_TRANSLATABLE = True
    undine_settings.MODELTRANSLATION_INCLUDE_TRANSLATIONS = True

    class TranslationFilterSet(FilterSet, model=TestModel, exclude=["pk"]): ...

    filters = TranslationFilterSet.__filter_map__
    assert sorted(filters) == [
        "name_contains",
        "name_en_contains",
        "name_en_endswith",
        "name_en_exact",
        "name_en_gt",
        "name_en_gte",
        "name_en_icontains",
        "name_en_iendswith",
        "name_en_iexact",
        "name_en_in",
        "name_en_iregex",
        "name_en_isnull",
        "name_en_istartswith",
        "name_en_lt",
        "name_en_lte",
        "name_en_range",
        "name_en_regex",
        "name_en_startswith",
        "name_endswith",
        "name_exact",
        "name_fi_contains",
        "name_fi_endswith",
        "name_fi_exact",
        "name_fi_gt",
        "name_fi_gte",
        "name_fi_icontains",
        "name_fi_iendswith",
        "name_fi_iexact",
        "name_fi_in",
        "name_fi_iregex",
        "name_fi_isnull",
        "name_fi_istartswith",
        "name_fi_lt",
        "name_fi_lte",
        "name_fi_range",
        "name_fi_regex",
        "name_fi_startswith",
        "name_gt",
        "name_gte",
        "name_icontains",
        "name_iendswith",
        "name_iexact",
        "name_in",
        "name_iregex",
        "name_isnull",
        "name_istartswith",
        "name_lt",
        "name_lte",
        "name_range",
        "name_regex",
        "name_startswith",
    ]


def test_modeltranslation__filterset_filters__only_translatable(undine_settings):
    undine_settings.MODELTRANSLATION_INCLUDE_TRANSLATABLE = True
    undine_settings.MODELTRANSLATION_INCLUDE_TRANSLATIONS = False

    class TranslationFilterSet(FilterSet, model=TestModel, exclude=["pk"]): ...

    filters = TranslationFilterSet.__filter_map__
    assert sorted(filters) == [
        "name_contains",
        "name_endswith",
        "name_exact",
        "name_gt",
        "name_gte",
        "name_icontains",
        "name_iendswith",
        "name_iexact",
        "name_in",
        "name_iregex",
        "name_isnull",
        "name_istartswith",
        "name_lt",
        "name_lte",
        "name_range",
        "name_regex",
        "name_startswith",
    ]


def test_modeltranslation__filterset_filters__only_translations(undine_settings):
    undine_settings.MODELTRANSLATION_INCLUDE_TRANSLATABLE = False
    undine_settings.MODELTRANSLATION_INCLUDE_TRANSLATIONS = True

    class TranslationFilterSet(FilterSet, model=TestModel, exclude=["pk"]): ...

    filters = TranslationFilterSet.__filter_map__
    assert sorted(filters) == [
        "name_en_contains",
        "name_en_endswith",
        "name_en_exact",
        "name_en_gt",
        "name_en_gte",
        "name_en_icontains",
        "name_en_iendswith",
        "name_en_iexact",
        "name_en_in",
        "name_en_iregex",
        "name_en_isnull",
        "name_en_istartswith",
        "name_en_lt",
        "name_en_lte",
        "name_en_range",
        "name_en_regex",
        "name_en_startswith",
        "name_fi_contains",
        "name_fi_endswith",
        "name_fi_exact",
        "name_fi_gt",
        "name_fi_gte",
        "name_fi_icontains",
        "name_fi_iendswith",
        "name_fi_iexact",
        "name_fi_in",
        "name_fi_iregex",
        "name_fi_isnull",
        "name_fi_istartswith",
        "name_fi_lt",
        "name_fi_lte",
        "name_fi_range",
        "name_fi_regex",
        "name_fi_startswith",
    ]


def test_modeltranslation__orderset_orders__include_translatable_and_translations(undine_settings):
    undine_settings.MODELTRANSLATION_INCLUDE_TRANSLATABLE = True
    undine_settings.MODELTRANSLATION_INCLUDE_TRANSLATIONS = True

    class TranslationOrderSet(OrderSet, model=TestModel, exclude=["pk"]): ...

    orders = TranslationOrderSet.__order_map__
    assert sorted(orders) == ["name", "name_en", "name_fi"]


def test_modeltranslation__orderset_orders__only_translatable(undine_settings):
    undine_settings.MODELTRANSLATION_INCLUDE_TRANSLATABLE = True
    undine_settings.MODELTRANSLATION_INCLUDE_TRANSLATIONS = False

    class TranslationOrderSet(OrderSet, model=TestModel, exclude=["pk"]): ...

    orders = TranslationOrderSet.__order_map__
    assert sorted(orders) == ["name"]


def test_modeltranslation__orderset_orders__only_translations(undine_settings):
    undine_settings.MODELTRANSLATION_INCLUDE_TRANSLATABLE = False
    undine_settings.MODELTRANSLATION_INCLUDE_TRANSLATIONS = True

    class TranslationOrderSet(OrderSet, model=TestModel, exclude=["pk"]): ...

    orders = TranslationOrderSet.__order_map__
    assert sorted(orders) == ["name_en", "name_fi"]
