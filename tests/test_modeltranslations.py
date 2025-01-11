from django.db.models import CharField, Model
from graphql import GraphQLNonNull, GraphQLString
from modeltranslation.decorators import register
from modeltranslation.translator import TranslationOptions

from undine import QueryType


class TestModel(Model):
    name = CharField(max_length=255)

    class Meta:
        managed = False
        app_label = "tests"

    def __str__(self) -> str:
        return self.name


@register(TestModel)
class TestModelOptions(TranslationOptions):
    fields = ["name"]


def test_translated_fields__include_translatable_and_translations(undine_settings):
    undine_settings.MODELTRANSLATION_INCLUDE_TRANSLATABLE = True
    undine_settings.MODELTRANSLATION_INCLUDE_TRANSLATIONS = True

    class TranslatedType(QueryType, model=TestModel): ...

    fields = TranslatedType.__field_map__
    assert sorted(fields) == ["name", "name_en", "name_fi", "pk"]

    name_en_field = fields["name"].as_graphql_field()
    assert name_en_field.type == GraphQLNonNull(GraphQLString)

    name_en_field = fields["name_en"].as_graphql_field()
    assert name_en_field.type == GraphQLString

    name_fi_field = fields["name_fi"].as_graphql_field()
    assert name_fi_field.type == GraphQLString


def test_translated_fields__only_translatable(undine_settings):
    undine_settings.MODELTRANSLATION_INCLUDE_TRANSLATABLE = True
    undine_settings.MODELTRANSLATION_INCLUDE_TRANSLATIONS = False

    class TranslatedType(QueryType, model=TestModel): ...

    fields = TranslatedType.__field_map__
    assert sorted(fields) == ["name", "pk"]

    name_en_field = fields["name"].as_graphql_field()
    assert name_en_field.type == GraphQLNonNull(GraphQLString)


def test_translated_fields__only_translations(undine_settings):
    undine_settings.MODELTRANSLATION_INCLUDE_TRANSLATABLE = False
    undine_settings.MODELTRANSLATION_INCLUDE_TRANSLATIONS = True

    class TranslatedType(QueryType, model=TestModel): ...

    fields = TranslatedType.__field_map__
    assert sorted(fields) == ["name_en", "name_fi", "pk"]

    name_en_field = fields["name_en"].as_graphql_field()
    assert name_en_field.type == GraphQLString

    name_fi_field = fields["name_fi"].as_graphql_field()
    assert name_fi_field.type == GraphQLString
