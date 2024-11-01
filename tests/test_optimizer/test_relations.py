import pytest

from example_project.app.models import (
    Comment,
    Example,
    ForwardManyToMany,
    ForwardManyToManyForRelated,
    ForwardManyToOne,
    ForwardManyToOneForRelated,
    ForwardOneToOne,
    ForwardOneToOneForRelated,
    Person,
    Project,
    ReverseManyToMany,
    ReverseManyToManyToForwardManyToMany,
    ReverseManyToManyToForwardManyToOne,
    ReverseManyToManyToForwardOneToOne,
    ReverseManyToManyToReverseManyToMany,
    ReverseManyToManyToReverseOneToMany,
    ReverseManyToManyToReverseOneToOne,
    ReverseOneToMany,
    ReverseOneToManyToForwardManyToMany,
    ReverseOneToManyToForwardManyToOne,
    ReverseOneToManyToForwardOneToOne,
    ReverseOneToManyToReverseManyToMany,
    ReverseOneToManyToReverseOneToMany,
    ReverseOneToManyToReverseOneToOne,
    ReverseOneToOne,
    ReverseOneToOneToForwardManyToMany,
    ReverseOneToOneToForwardManyToOne,
    ReverseOneToOneToForwardOneToOne,
    ReverseOneToOneToReverseManyToMany,
    ReverseOneToOneToReverseOneToMany,
    ReverseOneToOneToReverseOneToOne,
    Task,
    TaskTypeChoices,
    Team,
)
from tests.factories import CommentFactory, PersonFactory, ProjectFactory, TaskFactory, TeamFactory
from tests.factories.example import ExampleFactory
from undine import Entrypoint, Field, QueryType, create_schema

###############################################################################################


def example_schema():
    class ExampleType(QueryType, model=Example, exclude=["named_relation"]): ...

    class ForwardOneToOneType(QueryType, model=ForwardOneToOne): ...

    class ForwardManyToOneType(QueryType, model=ForwardManyToOne): ...

    class ForwardManyToManyType(QueryType, model=ForwardManyToMany): ...

    class ReverseOneToOneType(QueryType, model=ReverseOneToOne): ...

    class ReverseOneToManyType(QueryType, model=ReverseOneToMany): ...

    class ReverseManyToManyType(QueryType, model=ReverseManyToMany): ...

    class ForwardOneToOneForRelatedType(QueryType, model=ForwardOneToOneForRelated): ...

    class ForwardManyToOneForRelatedType(QueryType, model=ForwardManyToOneForRelated): ...

    class ForwardManyToManyForRelatedType(QueryType, model=ForwardManyToManyForRelated): ...

    class ReverseOneToOneToForwardOneToOneType(QueryType, model=ReverseOneToOneToForwardOneToOne): ...

    class ReverseOneToOneToForwardManyToOneType(QueryType, model=ReverseOneToOneToForwardManyToOne): ...

    class ReverseOneToOneToForwardManyToManyType(QueryType, model=ReverseOneToOneToForwardManyToMany): ...

    class ReverseOneToOneToReverseOneToOneType(QueryType, model=ReverseOneToOneToReverseOneToOne): ...

    class ReverseOneToOneToReverseOneToManyType(QueryType, model=ReverseOneToOneToReverseOneToMany): ...

    class ReverseOneToOneToReverseManyToManyType(QueryType, model=ReverseOneToOneToReverseManyToMany): ...

    class ReverseOneToManyToForwardOneToOneType(QueryType, model=ReverseOneToManyToForwardOneToOne): ...

    class ReverseOneToManyToForwardManyToOneType(QueryType, model=ReverseOneToManyToForwardManyToOne): ...

    class ReverseOneToManyToForwardManyToManyType(QueryType, model=ReverseOneToManyToForwardManyToMany): ...

    class ReverseOneToManyToReverseOneToOneType(QueryType, model=ReverseOneToManyToReverseOneToOne): ...

    class ReverseOneToManyToReverseOneToManyType(QueryType, model=ReverseOneToManyToReverseOneToMany): ...

    class ReverseOneToManyToReverseManyToManyType(QueryType, model=ReverseOneToManyToReverseManyToMany): ...

    class ReverseManyToManyToForwardOneToOneType(QueryType, model=ReverseManyToManyToForwardOneToOne): ...

    class ReverseManyToManyToForwardManyToOneType(QueryType, model=ReverseManyToManyToForwardManyToOne): ...

    class ReverseManyToManyToForwardManyToManyType(QueryType, model=ReverseManyToManyToForwardManyToMany): ...

    class ReverseManyToManyToReverseOneToOneType(QueryType, model=ReverseManyToManyToReverseOneToOne): ...

    class ReverseManyToManyToReverseOneToManyType(QueryType, model=ReverseManyToManyToReverseOneToMany): ...

    class ReverseManyToManyToReverseManyToManyType(QueryType, model=ReverseManyToManyToReverseManyToMany): ...

    class Query:
        examples = Entrypoint(ExampleType, many=True)

    return create_schema(query_class=Query)


@pytest.mark.django_db
def test_relations__forward_one_to_one__forward_one_to_one(graphql, undine_settings):
    undine_settings.SCHEMA = example_schema()

    ExampleFactory.create(forward_one_to_one_field__forward_one_to_one_field__name="1")
    ExampleFactory.create(forward_one_to_one_field__forward_one_to_one_field__name="2")
    ExampleFactory.create(forward_one_to_one_field__forward_one_to_one_field__name="3")

    query = """
        query {
          examples {
            forwardOneToOneField {
              forwardOneToOneField {
                name
              }
            }
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    # 1 query for all examples, forward one-to-one relations, and nested forward one-to-one relations
    response.assert_query_count(1)

    assert response.first_query_object == [
        {"forwardOneToOneField": {"forwardOneToOneField": {"name": "1"}}},
        {"forwardOneToOneField": {"forwardOneToOneField": {"name": "2"}}},
        {"forwardOneToOneField": {"forwardOneToOneField": {"name": "3"}}},
    ]


@pytest.mark.django_db
def test_relations__forward_one_to_one__forward_many_to_one(graphql, undine_settings):
    undine_settings.SCHEMA = example_schema()

    ExampleFactory.create(forward_one_to_one_field__forward_many_to_one_field__name="1")
    ExampleFactory.create(forward_one_to_one_field__forward_many_to_one_field__name="2")
    ExampleFactory.create(forward_one_to_one_field__forward_many_to_one_field__name="3")

    query = """
        query {
          examples {
            forwardOneToOneField {
              forwardManyToOneField {
                name
              }
            }
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    # 1 query for all examples, forward one-to-one relations, and nested forward many-to-one relations
    response.assert_query_count(1)

    assert response.first_query_object == [
        {"forwardOneToOneField": {"forwardManyToOneField": {"name": "1"}}},
        {"forwardOneToOneField": {"forwardManyToOneField": {"name": "2"}}},
        {"forwardOneToOneField": {"forwardManyToOneField": {"name": "3"}}},
    ]


@pytest.mark.django_db
def test_relations__forward_one_to_one__forward_many_to_many(graphql, undine_settings):
    undine_settings.SCHEMA = example_schema()

    ExampleFactory.create(forward_one_to_one_field__forward_many_to_many_fields__name="1")
    ExampleFactory.create(forward_one_to_one_field__forward_many_to_many_fields__name="2")
    ExampleFactory.create(forward_one_to_one_field__forward_many_to_many_fields__name="3")

    query = """
        query {
          examples {
            forwardOneToOneField {
              forwardManyToManyFields {
                name
              }
            }
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    # 1 query for all examples, forward one-to-one relations
    # 1 query for all nested forward many-to-many relations
    response.assert_query_count(2)

    assert response.first_query_object == [
        {"forwardOneToOneField": {"forwardManyToManyFields": [{"name": "1"}]}},
        {"forwardOneToOneField": {"forwardManyToManyFields": [{"name": "2"}]}},
        {"forwardOneToOneField": {"forwardManyToManyFields": [{"name": "3"}]}},
    ]


@pytest.mark.django_db
def test_relations__forward_one_to_one__reverse_one_to_one(graphql, undine_settings):
    undine_settings.SCHEMA = example_schema()

    ExampleFactory.create(forward_one_to_one_field__reverse_one_to_one_rel__name="1")
    ExampleFactory.create(forward_one_to_one_field__reverse_one_to_one_rel__name="2")
    ExampleFactory.create(forward_one_to_one_field__reverse_one_to_one_rel__name="3")

    query = """
        query {
          examples {
            forwardOneToOneField {
              reverseOneToOneRel {
                name
              }
            }
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    # 1 query for all examples, forward one-to-one relations and nested reverse one-to-one relations
    response.assert_query_count(1)

    assert response.first_query_object == [
        {"forwardOneToOneField": {"reverseOneToOneRel": {"name": "1"}}},
        {"forwardOneToOneField": {"reverseOneToOneRel": {"name": "2"}}},
        {"forwardOneToOneField": {"reverseOneToOneRel": {"name": "3"}}},
    ]


@pytest.mark.django_db
def test_relations__forward_one_to_one__reverse_one_to_many(graphql, undine_settings):
    undine_settings.SCHEMA = example_schema()

    ExampleFactory.create(forward_one_to_one_field__reverse_one_to_many_rels__name="1")
    ExampleFactory.create(forward_one_to_one_field__reverse_one_to_many_rels__name="2")
    ExampleFactory.create(forward_one_to_one_field__reverse_one_to_many_rels__name="3")

    query = """
        query {
          examples {
            forwardOneToOneField {
              reverseOneToManyRels {
                name
              }
            }
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    # 1 query for all examples, forward one-to-one relations
    # 1 query for all nested reverse one-to-many relations
    response.assert_query_count(2)

    assert response.first_query_object == [
        {"forwardOneToOneField": {"reverseOneToManyRels": [{"name": "1"}]}},
        {"forwardOneToOneField": {"reverseOneToManyRels": [{"name": "2"}]}},
        {"forwardOneToOneField": {"reverseOneToManyRels": [{"name": "3"}]}},
    ]


@pytest.mark.django_db
def test_relations__forward_one_to_one__reverse_many_to_many(graphql, undine_settings):
    undine_settings.SCHEMA = example_schema()

    ExampleFactory.create(forward_one_to_one_field__reverse_many_to_many_rels__name="1")
    ExampleFactory.create(forward_one_to_one_field__reverse_many_to_many_rels__name="2")
    ExampleFactory.create(forward_one_to_one_field__reverse_many_to_many_rels__name="3")

    query = """
        query {
          examples {
            forwardOneToOneField {
              reverseManyToManyRels {
                name
              }
            }
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    # 1 query for all examples, forward one-to-one relations
    # 1 query for all nested reverse many-to-many relations
    response.assert_query_count(2)

    assert response.first_query_object == [
        {"forwardOneToOneField": {"reverseManyToManyRels": [{"name": "1"}]}},
        {"forwardOneToOneField": {"reverseManyToManyRels": [{"name": "2"}]}},
        {"forwardOneToOneField": {"reverseManyToManyRels": [{"name": "3"}]}},
    ]


###############################################################################################


@pytest.mark.django_db
def test_relations__forward_many_to_one__forward_one_to_one(graphql, undine_settings):
    undine_settings.SCHEMA = example_schema()

    ExampleFactory.create(forward_many_to_one_field__forward_one_to_one_field__name="1")
    ExampleFactory.create(forward_many_to_one_field__forward_one_to_one_field__name="2")
    ExampleFactory.create(forward_many_to_one_field__forward_one_to_one_field__name="3")

    query = """
        query {
          examples {
            forwardManyToOneField {
              forwardOneToOneField {
                name
              }
            }
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    # 1 query for all examples, forward many-to-one relations, and nested forward one-to-one relations
    response.assert_query_count(1)

    assert response.first_query_object == [
        {"forwardManyToOneField": {"forwardOneToOneField": {"name": "1"}}},
        {"forwardManyToOneField": {"forwardOneToOneField": {"name": "2"}}},
        {"forwardManyToOneField": {"forwardOneToOneField": {"name": "3"}}},
    ]


@pytest.mark.django_db
def test_relations__forward_many_to_one__forward_many_to_one(graphql, undine_settings):
    undine_settings.SCHEMA = example_schema()

    ExampleFactory.create(forward_many_to_one_field__forward_many_to_one_field__name="1")
    ExampleFactory.create(forward_many_to_one_field__forward_many_to_one_field__name="2")
    ExampleFactory.create(forward_many_to_one_field__forward_many_to_one_field__name="3")

    query = """
        query {
          examples {
            forwardManyToOneField {
              forwardManyToOneField {
                name
              }
            }
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    # 1 query for all examples, forward many-to-one relations, and nested forward many-to-one relations
    response.assert_query_count(1)

    assert response.first_query_object == [
        {"forwardManyToOneField": {"forwardManyToOneField": {"name": "1"}}},
        {"forwardManyToOneField": {"forwardManyToOneField": {"name": "2"}}},
        {"forwardManyToOneField": {"forwardManyToOneField": {"name": "3"}}},
    ]


@pytest.mark.django_db
def test_relations__forward_many_to_one__forward_many_to_many(graphql, undine_settings):
    undine_settings.SCHEMA = example_schema()

    ExampleFactory.create(forward_many_to_one_field__forward_many_to_many_fields__name="1")
    ExampleFactory.create(forward_many_to_one_field__forward_many_to_many_fields__name="2")
    ExampleFactory.create(forward_many_to_one_field__forward_many_to_many_fields__name="3")

    query = """
        query {
          examples {
            forwardManyToOneField {
              forwardManyToManyFields {
                name
              }
            }
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    # 1 query for all examples, forward many-to-one relations
    # 1 query for all nested forward many-to-many relations
    response.assert_query_count(2)

    assert response.first_query_object == [
        {"forwardManyToOneField": {"forwardManyToManyFields": [{"name": "1"}]}},
        {"forwardManyToOneField": {"forwardManyToManyFields": [{"name": "2"}]}},
        {"forwardManyToOneField": {"forwardManyToManyFields": [{"name": "3"}]}},
    ]


@pytest.mark.django_db
def test_relations__forward_many_to_one__reverse_one_to_one(graphql, undine_settings):
    undine_settings.SCHEMA = example_schema()

    ExampleFactory.create(forward_many_to_one_field__reverse_one_to_one_rel__name="1")
    ExampleFactory.create(forward_many_to_one_field__reverse_one_to_one_rel__name="2")
    ExampleFactory.create(forward_many_to_one_field__reverse_one_to_one_rel__name="3")

    query = """
        query {
          examples {
            forwardManyToOneField {
              reverseOneToOneRel {
                name
              }
            }
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    # 1 query for all examples, forward many-to-one relations and nested reverse one-to-one relations
    response.assert_query_count(1)

    assert response.first_query_object == [
        {"forwardManyToOneField": {"reverseOneToOneRel": {"name": "1"}}},
        {"forwardManyToOneField": {"reverseOneToOneRel": {"name": "2"}}},
        {"forwardManyToOneField": {"reverseOneToOneRel": {"name": "3"}}},
    ]


@pytest.mark.django_db
def test_relations__forward_many_to_one__reverse_one_to_many(graphql, undine_settings):
    undine_settings.SCHEMA = example_schema()

    ExampleFactory.create(forward_many_to_one_field__reverse_one_to_many_rels__name="1")
    ExampleFactory.create(forward_many_to_one_field__reverse_one_to_many_rels__name="2")
    ExampleFactory.create(forward_many_to_one_field__reverse_one_to_many_rels__name="3")

    query = """
        query {
          examples {
            forwardManyToOneField {
              reverseOneToManyRels {
                name
              }
            }
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    # 1 query for all examples, forward many-to-one relations
    # 1 query for all nested reverse one-to-many relations
    response.assert_query_count(2)

    assert response.first_query_object == [
        {"forwardManyToOneField": {"reverseOneToManyRels": [{"name": "1"}]}},
        {"forwardManyToOneField": {"reverseOneToManyRels": [{"name": "2"}]}},
        {"forwardManyToOneField": {"reverseOneToManyRels": [{"name": "3"}]}},
    ]


@pytest.mark.django_db
def test_relations__forward_many_to_one__reverse_many_to_many(graphql, undine_settings):
    undine_settings.SCHEMA = example_schema()

    ExampleFactory.create(forward_many_to_one_field__reverse_many_to_many_rels__name="1")
    ExampleFactory.create(forward_many_to_one_field__reverse_many_to_many_rels__name="2")
    ExampleFactory.create(forward_many_to_one_field__reverse_many_to_many_rels__name="3")

    query = """
        query {
          examples {
            forwardManyToOneField {
              reverseManyToManyRels {
                name
              }
            }
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    # 1 query for all examples, forward many-to-one relations
    # 1 query for all nested reverse many-to-many relations
    response.assert_query_count(2)

    assert response.first_query_object == [
        {"forwardManyToOneField": {"reverseManyToManyRels": [{"name": "1"}]}},
        {"forwardManyToOneField": {"reverseManyToManyRels": [{"name": "2"}]}},
        {"forwardManyToOneField": {"reverseManyToManyRels": [{"name": "3"}]}},
    ]


###############################################################################################


@pytest.mark.django_db
def test_relations__forward_many_to_many__forward_one_to_one(graphql, undine_settings):
    undine_settings.SCHEMA = example_schema()

    ExampleFactory.create(forward_many_to_many_fields__forward_one_to_one_field__name="1")
    ExampleFactory.create(forward_many_to_many_fields__forward_one_to_one_field__name="2")
    ExampleFactory.create(forward_many_to_many_fields__forward_one_to_one_field__name="3")

    query = """
        query {
          examples {
            forwardManyToManyFields {
              forwardOneToOneField {
                name
              }
            }
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    # 1 query for all examples
    # 1 query fo all forward many-to-many relations, and nested forward one-to-one relations
    response.assert_query_count(2)

    assert response.first_query_object == [
        {"forwardManyToManyFields": [{"forwardOneToOneField": {"name": "1"}}]},
        {"forwardManyToManyFields": [{"forwardOneToOneField": {"name": "2"}}]},
        {"forwardManyToManyFields": [{"forwardOneToOneField": {"name": "3"}}]},
    ]


@pytest.mark.django_db
def test_relations__forward_many_to_many__forward_many_to_one(graphql, undine_settings):
    undine_settings.SCHEMA = example_schema()

    ExampleFactory.create(forward_many_to_many_fields__forward_many_to_one_field__name="1")
    ExampleFactory.create(forward_many_to_many_fields__forward_many_to_one_field__name="2")
    ExampleFactory.create(forward_many_to_many_fields__forward_many_to_one_field__name="3")

    query = """
        query {
          examples {
            forwardManyToManyFields {
              forwardManyToOneField {
                name
              }
            }
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    # 1 query for all examples
    # 1 query fo all forward many-to-many relations, and nested forward many-to-one relations
    response.assert_query_count(2)

    assert response.first_query_object == [
        {"forwardManyToManyFields": [{"forwardManyToOneField": {"name": "1"}}]},
        {"forwardManyToManyFields": [{"forwardManyToOneField": {"name": "2"}}]},
        {"forwardManyToManyFields": [{"forwardManyToOneField": {"name": "3"}}]},
    ]


@pytest.mark.django_db
def test_relations__forward_many_to_many__forward_many_to_many(graphql, undine_settings):
    undine_settings.SCHEMA = example_schema()

    ExampleFactory.create(forward_many_to_many_fields__forward_many_to_many_fields__name="1")
    ExampleFactory.create(forward_many_to_many_fields__forward_many_to_many_fields__name="2")
    ExampleFactory.create(forward_many_to_many_fields__forward_many_to_many_fields__name="3")

    query = """
        query {
          examples {
            forwardManyToManyFields {
              forwardManyToManyFields {
                name
              }
            }
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    # 1 query for all examples
    # 1 query fo all forward many-to-many relations
    # 1 query for all nested forward many-to-many relations
    response.assert_query_count(3)

    assert response.first_query_object == [
        {"forwardManyToManyFields": [{"forwardManyToManyFields": [{"name": "1"}]}]},
        {"forwardManyToManyFields": [{"forwardManyToManyFields": [{"name": "2"}]}]},
        {"forwardManyToManyFields": [{"forwardManyToManyFields": [{"name": "3"}]}]},
    ]


@pytest.mark.django_db
def test_relations__forward_many_to_many__reverse_one_to_one(graphql, undine_settings):
    undine_settings.SCHEMA = example_schema()

    ExampleFactory.create(forward_many_to_many_fields__reverse_one_to_one_rel__name="1")
    ExampleFactory.create(forward_many_to_many_fields__reverse_one_to_one_rel__name="2")
    ExampleFactory.create(forward_many_to_many_fields__reverse_one_to_one_rel__name="3")

    query = """
        query {
          examples {
            forwardManyToManyFields {
              reverseOneToOneRel {
                name
              }
            }
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    # 1 query for all examples
    # 1 query for all forward many-to-many relations and nested reverse one-to-one relations
    response.assert_query_count(2)

    assert response.first_query_object == [
        {"forwardManyToManyFields": [{"reverseOneToOneRel": {"name": "1"}}]},
        {"forwardManyToManyFields": [{"reverseOneToOneRel": {"name": "2"}}]},
        {"forwardManyToManyFields": [{"reverseOneToOneRel": {"name": "3"}}]},
    ]


@pytest.mark.django_db
def test_relations__forward_many_to_many__reverse_one_to_many(graphql, undine_settings):
    undine_settings.SCHEMA = example_schema()

    ExampleFactory.create(forward_many_to_many_fields__reverse_one_to_many_rels__name="1")
    ExampleFactory.create(forward_many_to_many_fields__reverse_one_to_many_rels__name="2")
    ExampleFactory.create(forward_many_to_many_fields__reverse_one_to_many_rels__name="3")

    query = """
        query {
          examples {
            forwardManyToManyFields {
              reverseOneToManyRels {
                name
              }
            }
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    # 1 query for all examples
    # 1 query for all forward many-to-many relations
    # 1 query for all nested reverse one-to-many relations
    response.assert_query_count(3)

    assert response.first_query_object == [
        {"forwardManyToManyFields": [{"reverseOneToManyRels": [{"name": "1"}]}]},
        {"forwardManyToManyFields": [{"reverseOneToManyRels": [{"name": "2"}]}]},
        {"forwardManyToManyFields": [{"reverseOneToManyRels": [{"name": "3"}]}]},
    ]


@pytest.mark.django_db
def test_relations__forward_many_to_many__reverse_many_to_many(graphql, undine_settings):
    undine_settings.SCHEMA = example_schema()

    ExampleFactory.create(forward_many_to_many_fields__reverse_many_to_many_rels__name="1")
    ExampleFactory.create(forward_many_to_many_fields__reverse_many_to_many_rels__name="2")
    ExampleFactory.create(forward_many_to_many_fields__reverse_many_to_many_rels__name="3")

    query = """
        query {
          examples {
            forwardManyToManyFields {
              reverseManyToManyRels {
                name
              }
            }
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    # 1 query for all examples
    # 1 query for all forward many-to-many relations
    # 1 query for all nested reverse many-to-many relations
    response.assert_query_count(3)

    assert response.first_query_object == [
        {"forwardManyToManyFields": [{"reverseManyToManyRels": [{"name": "1"}]}]},
        {"forwardManyToManyFields": [{"reverseManyToManyRels": [{"name": "2"}]}]},
        {"forwardManyToManyFields": [{"reverseManyToManyRels": [{"name": "3"}]}]},
    ]


###############################################################################################


@pytest.mark.django_db
def test_relations__reverse_one_to_one__forward_one_to_one(graphql, undine_settings):
    undine_settings.SCHEMA = example_schema()

    ExampleFactory.create(reverse_one_to_one_rel__forward_one_to_one_field__name="1")
    ExampleFactory.create(reverse_one_to_one_rel__forward_one_to_one_field__name="2")
    ExampleFactory.create(reverse_one_to_one_rel__forward_one_to_one_field__name="3")

    query = """
        query {
          examples {
            reverseOneToOneRel {
              forwardOneToOneField {
                name
              }
            }
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    # 1 query for all examples, reverse one-to-one relations, and nested forward one-to-one relations
    response.assert_query_count(1)

    assert response.first_query_object == [
        {"reverseOneToOneRel": {"forwardOneToOneField": {"name": "1"}}},
        {"reverseOneToOneRel": {"forwardOneToOneField": {"name": "2"}}},
        {"reverseOneToOneRel": {"forwardOneToOneField": {"name": "3"}}},
    ]


@pytest.mark.django_db
def test_relations__reverse_one_to_one__forward_many_to_one(graphql, undine_settings):
    undine_settings.SCHEMA = example_schema()

    ExampleFactory.create(reverse_one_to_one_rel__forward_many_to_one_field__name="1")
    ExampleFactory.create(reverse_one_to_one_rel__forward_many_to_one_field__name="2")
    ExampleFactory.create(reverse_one_to_one_rel__forward_many_to_one_field__name="3")

    query = """
        query {
          examples {
            reverseOneToOneRel {
              forwardManyToOneField {
                name
              }
            }
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    # 1 query for all examples, reverse one-to-one relations, and nested forward many-to-one relations
    response.assert_query_count(1)

    assert response.first_query_object == [
        {"reverseOneToOneRel": {"forwardManyToOneField": {"name": "1"}}},
        {"reverseOneToOneRel": {"forwardManyToOneField": {"name": "2"}}},
        {"reverseOneToOneRel": {"forwardManyToOneField": {"name": "3"}}},
    ]


@pytest.mark.django_db
def test_relations__reverse_one_to_one__forward_many_to_many(graphql, undine_settings):
    undine_settings.SCHEMA = example_schema()

    ExampleFactory.create(reverse_one_to_one_rel__forward_many_to_many_fields__name="1")
    ExampleFactory.create(reverse_one_to_one_rel__forward_many_to_many_fields__name="2")
    ExampleFactory.create(reverse_one_to_one_rel__forward_many_to_many_fields__name="3")

    query = """
        query {
          examples {
            reverseOneToOneRel {
              forwardManyToManyFields {
                name
              }
            }
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    # 1 query for all examples, reverse one-to-one relations
    # 1 query for all nested forward many-to-many relations
    response.assert_query_count(2)

    assert response.first_query_object == [
        {"reverseOneToOneRel": {"forwardManyToManyFields": [{"name": "1"}]}},
        {"reverseOneToOneRel": {"forwardManyToManyFields": [{"name": "2"}]}},
        {"reverseOneToOneRel": {"forwardManyToManyFields": [{"name": "3"}]}},
    ]


@pytest.mark.django_db
def test_relations__reverse_one_to_one__reverse_one_to_one(graphql, undine_settings):
    undine_settings.SCHEMA = example_schema()

    ExampleFactory.create(reverse_one_to_one_rel__reverse_one_to_one_rel__name="1")
    ExampleFactory.create(reverse_one_to_one_rel__reverse_one_to_one_rel__name="2")
    ExampleFactory.create(reverse_one_to_one_rel__reverse_one_to_one_rel__name="3")

    query = """
        query {
          examples {
            reverseOneToOneRel {
              reverseOneToOneRel {
                name
              }
            }
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    # 1 query for all examples, reverse one-to-one relations and nested reverse one-to-one relations
    response.assert_query_count(1)

    assert response.first_query_object == [
        {"reverseOneToOneRel": {"reverseOneToOneRel": {"name": "1"}}},
        {"reverseOneToOneRel": {"reverseOneToOneRel": {"name": "2"}}},
        {"reverseOneToOneRel": {"reverseOneToOneRel": {"name": "3"}}},
    ]


@pytest.mark.django_db
def test_relations__reverse_one_to_one__reverse_one_to_many(graphql, undine_settings):
    undine_settings.SCHEMA = example_schema()

    ExampleFactory.create(reverse_one_to_one_rel__reverse_one_to_many_rels__name="1")
    ExampleFactory.create(reverse_one_to_one_rel__reverse_one_to_many_rels__name="2")
    ExampleFactory.create(reverse_one_to_one_rel__reverse_one_to_many_rels__name="3")

    query = """
        query {
          examples {
            reverseOneToOneRel {
              reverseOneToManyRels {
                name
              }
            }
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    # 1 query for all examples, reverse one-to-one relations
    # 1 query for all nested reverse one-to-many relations
    response.assert_query_count(2)

    assert response.first_query_object == [
        {"reverseOneToOneRel": {"reverseOneToManyRels": [{"name": "1"}]}},
        {"reverseOneToOneRel": {"reverseOneToManyRels": [{"name": "2"}]}},
        {"reverseOneToOneRel": {"reverseOneToManyRels": [{"name": "3"}]}},
    ]


@pytest.mark.django_db
def test_relations__reverse_one_to_one__reverse_many_to_many(graphql, undine_settings):
    undine_settings.SCHEMA = example_schema()

    ExampleFactory.create(reverse_one_to_one_rel__reverse_many_to_many_rels__name="1")
    ExampleFactory.create(reverse_one_to_one_rel__reverse_many_to_many_rels__name="2")
    ExampleFactory.create(reverse_one_to_one_rel__reverse_many_to_many_rels__name="3")

    query = """
        query {
          examples {
            reverseOneToOneRel {
              reverseManyToManyRels {
                name
              }
            }
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    # 1 query for all examples, reverse one-to-one relations
    # 1 query for all nested reverse many-to-many relations
    response.assert_query_count(2)

    assert response.first_query_object == [
        {"reverseOneToOneRel": {"reverseManyToManyRels": [{"name": "1"}]}},
        {"reverseOneToOneRel": {"reverseManyToManyRels": [{"name": "2"}]}},
        {"reverseOneToOneRel": {"reverseManyToManyRels": [{"name": "3"}]}},
    ]


###############################################################################################


@pytest.mark.django_db
def test_relations__reverse_one_to_many__forward_one_to_one(graphql, undine_settings):
    undine_settings.SCHEMA = example_schema()

    ExampleFactory.create(reverse_one_to_many_rels__forward_one_to_one_field__name="1")
    ExampleFactory.create(reverse_one_to_many_rels__forward_one_to_one_field__name="2")
    ExampleFactory.create(reverse_one_to_many_rels__forward_one_to_one_field__name="3")

    query = """
        query {
          examples {
            reverseOneToManyRels {
              forwardOneToOneField {
                name
              }
            }
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    # 1 query for all examples
    # 1 query for all reverse one-to-many relations query and nested forward one-to-one relations
    response.assert_query_count(2)

    assert response.first_query_object == [
        {"reverseOneToManyRels": [{"forwardOneToOneField": {"name": "1"}}]},
        {"reverseOneToManyRels": [{"forwardOneToOneField": {"name": "2"}}]},
        {"reverseOneToManyRels": [{"forwardOneToOneField": {"name": "3"}}]},
    ]


@pytest.mark.django_db
def test_relations__reverse_one_to_many__forward_many_to_one(graphql, undine_settings):
    undine_settings.SCHEMA = example_schema()

    ExampleFactory.create(reverse_one_to_many_rels__forward_many_to_one_field__name="1")
    ExampleFactory.create(reverse_one_to_many_rels__forward_many_to_one_field__name="2")
    ExampleFactory.create(reverse_one_to_many_rels__forward_many_to_one_field__name="3")

    query = """
        query {
          examples {
            reverseOneToManyRels {
              forwardManyToOneField {
                name
              }
            }
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    # 1 query for all examples
    # 1 query for all reverse one-to-many relations query and nested forward many-to-one relations
    response.assert_query_count(2)

    assert response.first_query_object == [
        {"reverseOneToManyRels": [{"forwardManyToOneField": {"name": "1"}}]},
        {"reverseOneToManyRels": [{"forwardManyToOneField": {"name": "2"}}]},
        {"reverseOneToManyRels": [{"forwardManyToOneField": {"name": "3"}}]},
    ]


@pytest.mark.django_db
def test_relations__reverse_one_to_many__forward_many_to_many(graphql, undine_settings):
    undine_settings.SCHEMA = example_schema()

    ExampleFactory.create(reverse_one_to_many_rels__forward_many_to_many_fields__name="1")
    ExampleFactory.create(reverse_one_to_many_rels__forward_many_to_many_fields__name="2")
    ExampleFactory.create(reverse_one_to_many_rels__forward_many_to_many_fields__name="3")

    query = """
        query {
          examples {
            reverseOneToManyRels {
              forwardManyToManyFields {
                name
              }
            }
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    # 1 query for all examples
    # 1 query for all reverse one-to-many relations
    # 1 query for all nested forward many-to-many relations
    response.assert_query_count(3)

    assert response.first_query_object == [
        {"reverseOneToManyRels": [{"forwardManyToManyFields": [{"name": "1"}]}]},
        {"reverseOneToManyRels": [{"forwardManyToManyFields": [{"name": "2"}]}]},
        {"reverseOneToManyRels": [{"forwardManyToManyFields": [{"name": "3"}]}]},
    ]


@pytest.mark.django_db
def test_relations__reverse_one_to_many__reverse_one_to_one(graphql, undine_settings):
    undine_settings.SCHEMA = example_schema()

    ExampleFactory.create(reverse_one_to_many_rels__reverse_one_to_one_rel__name="1")
    ExampleFactory.create(reverse_one_to_many_rels__reverse_one_to_one_rel__name="2")
    ExampleFactory.create(reverse_one_to_many_rels__reverse_one_to_one_rel__name="3")

    query = """
        query {
          examples {
            reverseOneToManyRels {
              reverseOneToOneRel {
                name
              }
            }
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    # 1 query for all examples
    # 1 query for all reverse one-to-many relations query and nested reverse one-to-one relations
    response.assert_query_count(2)

    assert response.first_query_object == [
        {"reverseOneToManyRels": [{"reverseOneToOneRel": {"name": "1"}}]},
        {"reverseOneToManyRels": [{"reverseOneToOneRel": {"name": "2"}}]},
        {"reverseOneToManyRels": [{"reverseOneToOneRel": {"name": "3"}}]},
    ]


@pytest.mark.django_db
def test_relations__reverse_one_to_many__reverse_one_to_many(graphql, undine_settings):
    undine_settings.SCHEMA = example_schema()

    ExampleFactory.create(reverse_one_to_many_rels__reverse_one_to_many_rels__name="1")
    ExampleFactory.create(reverse_one_to_many_rels__reverse_one_to_many_rels__name="2")
    ExampleFactory.create(reverse_one_to_many_rels__reverse_one_to_many_rels__name="3")

    query = """
        query {
          examples {
            reverseOneToManyRels {
              reverseOneToManyRels {
                name
              }
            }
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    # 1 query for all examples
    # 1 query for all reverse one-to-many relations
    # 1 query for all nested reverse one-to-many relations
    response.assert_query_count(3)

    assert response.first_query_object == [
        {"reverseOneToManyRels": [{"reverseOneToManyRels": [{"name": "1"}]}]},
        {"reverseOneToManyRels": [{"reverseOneToManyRels": [{"name": "2"}]}]},
        {"reverseOneToManyRels": [{"reverseOneToManyRels": [{"name": "3"}]}]},
    ]


@pytest.mark.django_db
def test_relations__reverse_one_to_many__reverse_many_to_many(graphql, undine_settings):
    undine_settings.SCHEMA = example_schema()

    ExampleFactory.create(reverse_one_to_many_rels__reverse_many_to_many_rels__name="1")
    ExampleFactory.create(reverse_one_to_many_rels__reverse_many_to_many_rels__name="2")
    ExampleFactory.create(reverse_one_to_many_rels__reverse_many_to_many_rels__name="3")

    query = """
        query {
          examples {
            reverseOneToManyRels {
              reverseManyToManyRels {
                name
              }
            }
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    # 1 query for all examples
    # 1 query for all reverse one-to-many relations
    # 1 query for all nested reverse many-to-many relations
    response.assert_query_count(3)

    assert response.first_query_object == [
        {"reverseOneToManyRels": [{"reverseManyToManyRels": [{"name": "1"}]}]},
        {"reverseOneToManyRels": [{"reverseManyToManyRels": [{"name": "2"}]}]},
        {"reverseOneToManyRels": [{"reverseManyToManyRels": [{"name": "3"}]}]},
    ]


###############################################################################################


@pytest.mark.django_db
def test_relations__reverse_many_to_many__forward_one_to_one(graphql, undine_settings):
    undine_settings.SCHEMA = example_schema()

    ExampleFactory.create(reverse_many_to_many_rels__forward_one_to_one_field__name="1")
    ExampleFactory.create(reverse_many_to_many_rels__forward_one_to_one_field__name="2")
    ExampleFactory.create(reverse_many_to_many_rels__forward_one_to_one_field__name="3")

    query = """
        query {
          examples {
            reverseManyToManyRels {
              forwardOneToOneField {
                name
              }
            }
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    # 1 query for all examples
    # 1 query for all reverse many-to-many relations and nested forward one-to-one relations
    response.assert_query_count(2)

    assert response.first_query_object == [
        {"reverseManyToManyRels": [{"forwardOneToOneField": {"name": "1"}}]},
        {"reverseManyToManyRels": [{"forwardOneToOneField": {"name": "2"}}]},
        {"reverseManyToManyRels": [{"forwardOneToOneField": {"name": "3"}}]},
    ]


@pytest.mark.django_db
def test_relations__reverse_many_to_many__forward_many_to_one(graphql, undine_settings):
    undine_settings.SCHEMA = example_schema()

    ExampleFactory.create(reverse_many_to_many_rels__forward_many_to_one_field__name="1")
    ExampleFactory.create(reverse_many_to_many_rels__forward_many_to_one_field__name="2")
    ExampleFactory.create(reverse_many_to_many_rels__forward_many_to_one_field__name="3")

    query = """
        query {
          examples {
            reverseManyToManyRels {
              forwardManyToOneField {
                name
              }
            }
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    # 1 query for all examples
    # 1 query for all reverse many-to-many relations and nested forward many-to-one relations
    response.assert_query_count(2)

    assert response.first_query_object == [
        {"reverseManyToManyRels": [{"forwardManyToOneField": {"name": "1"}}]},
        {"reverseManyToManyRels": [{"forwardManyToOneField": {"name": "2"}}]},
        {"reverseManyToManyRels": [{"forwardManyToOneField": {"name": "3"}}]},
    ]


@pytest.mark.django_db
def test_relations__reverse_many_to_many__forward_many_to_many(graphql, undine_settings):
    undine_settings.SCHEMA = example_schema()

    ExampleFactory.create(reverse_many_to_many_rels__forward_many_to_many_fields__name="1")
    ExampleFactory.create(reverse_many_to_many_rels__forward_many_to_many_fields__name="2")
    ExampleFactory.create(reverse_many_to_many_rels__forward_many_to_many_fields__name="3")

    query = """
        query {
          examples {
            reverseManyToManyRels {
              forwardManyToManyFields {
                name
              }
            }
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    # 1 query for all examples
    # 1 query for all reverse many-to-many relations
    # 1 query for all nested forward many-to-many relations
    response.assert_query_count(3)

    assert response.first_query_object == [
        {"reverseManyToManyRels": [{"forwardManyToManyFields": [{"name": "1"}]}]},
        {"reverseManyToManyRels": [{"forwardManyToManyFields": [{"name": "2"}]}]},
        {"reverseManyToManyRels": [{"forwardManyToManyFields": [{"name": "3"}]}]},
    ]


@pytest.mark.django_db
def test_relations__reverse_many_to_many__reverse_one_to_one(graphql, undine_settings):
    undine_settings.SCHEMA = example_schema()

    ExampleFactory.create(reverse_many_to_many_rels__reverse_one_to_one_rel__name="1")
    ExampleFactory.create(reverse_many_to_many_rels__reverse_one_to_one_rel__name="2")
    ExampleFactory.create(reverse_many_to_many_rels__reverse_one_to_one_rel__name="3")

    query = """
        query {
          examples {
            reverseManyToManyRels {
              reverseOneToOneRel {
                name
              }
            }
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    # 1 query for all examples
    # 1 query for all reverse many-to-many relations and nested reverse one-to-one relations
    response.assert_query_count(2)

    assert response.first_query_object == [
        {"reverseManyToManyRels": [{"reverseOneToOneRel": {"name": "1"}}]},
        {"reverseManyToManyRels": [{"reverseOneToOneRel": {"name": "2"}}]},
        {"reverseManyToManyRels": [{"reverseOneToOneRel": {"name": "3"}}]},
    ]


@pytest.mark.django_db
def test_relations__reverse_many_to_many__reverse_one_to_many(graphql, undine_settings):
    undine_settings.SCHEMA = example_schema()

    ExampleFactory.create(reverse_many_to_many_rels__reverse_one_to_many_rels__name="1")
    ExampleFactory.create(reverse_many_to_many_rels__reverse_one_to_many_rels__name="2")
    ExampleFactory.create(reverse_many_to_many_rels__reverse_one_to_many_rels__name="3")

    query = """
        query {
          examples {
            reverseManyToManyRels {
              reverseOneToManyRels {
                name
              }
            }
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    # 1 query for all examples
    # 1 query for all reverse many-to-many relations
    # 1 query for all nested reverse one-to-many relations
    response.assert_query_count(3)

    assert response.first_query_object == [
        {"reverseManyToManyRels": [{"reverseOneToManyRels": [{"name": "1"}]}]},
        {"reverseManyToManyRels": [{"reverseOneToManyRels": [{"name": "2"}]}]},
        {"reverseManyToManyRels": [{"reverseOneToManyRels": [{"name": "3"}]}]},
    ]


@pytest.mark.django_db
def test_relations__reverse_many_to_many__reverse_many_to_many(graphql, undine_settings):
    undine_settings.SCHEMA = example_schema()

    ExampleFactory.create(reverse_many_to_many_rels__reverse_many_to_many_rels__name="1")
    ExampleFactory.create(reverse_many_to_many_rels__reverse_many_to_many_rels__name="2")
    ExampleFactory.create(reverse_many_to_many_rels__reverse_many_to_many_rels__name="3")

    query = """
        query {
          examples {
            reverseManyToManyRels {
              reverseManyToManyRels {
                name
              }
            }
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    # 1 query for all examples
    # 1 query for all reverse many-to-many relations
    # 1 query for all nested reverse many-to-many relations
    response.assert_query_count(3)

    assert response.first_query_object == [
        {"reverseManyToManyRels": [{"reverseManyToManyRels": [{"name": "1"}]}]},
        {"reverseManyToManyRels": [{"reverseManyToManyRels": [{"name": "2"}]}]},
        {"reverseManyToManyRels": [{"reverseManyToManyRels": [{"name": "3"}]}]},
    ]


###############################################################################################


@pytest.mark.django_db
def test_relations__generic_relation(graphql, undine_settings):
    class CommentType(QueryType, model=Comment, auto=False):
        contents = Field()

    class TaskType(QueryType, model=Task, auto=False):
        comments = Field(CommentType)

    class Query:
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query_class=Query)

    task = TaskFactory.create()
    CommentFactory.create(contents="foo", target=task)
    CommentFactory.create(contents="bar", target=task)

    query = """
        query {
          tasks {
            comments {
              contents
            }
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    # 1 query for all tasks
    # 1 query for all comments
    response.assert_query_count(2)

    assert response.data == {
        "tasks": [
            {
                "comments": [
                    {"contents": "foo"},
                    {"contents": "bar"},
                ],
            },
        ],
    }


@pytest.mark.django_db
def test_relations__generic_foreign_key(graphql, undine_settings):
    class TaskType(QueryType, model=Task, auto=False):
        type = Field()

    class ProjectType(QueryType, model=Project, auto=False):
        name = Field()

    class CommentType(QueryType, model=Comment, auto=False):
        target = Field()

    class Query:
        comments = Entrypoint(CommentType, many=True)

    undine_settings.SCHEMA = create_schema(query_class=Query)

    task = TaskFactory.create(type=TaskTypeChoices.STORY.value)
    project = ProjectFactory.create(name="project")
    CommentFactory.create(contents="foo", target=task)
    CommentFactory.create(contents="bar", target=project)

    query = """
        query {
          comments {
            target {
              ... on ProjectType {
                name
              }
              ... on TaskType {
                type
              }
            }
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    # 1 query for all comments
    # 1 query for all tasks related to the comments
    # 1 query for all projects related to the comments
    response.assert_query_count(3)

    assert response.data == {
        "comments": [
            {
                "target": {"type": "STORY"},
            },
            {
                "target": {"name": "project"},
            },
        ],
    }


@pytest.mark.django_db
def test_relations__generic_foreign_key__nested_relations(graphql, undine_settings):
    class TeamType(QueryType, model=Team, auto=False):
        name = Field()

    class ProjectType(QueryType, model=Project, auto=False):
        name = Field()
        team = Field(TeamType)

    class TaskType(QueryType, model=Task, auto=False):
        type = Field()
        project = Field(ProjectType)

    class CommentType(QueryType, model=Comment, auto=False):
        target = Field()

    class Query:
        comments = Entrypoint(CommentType, many=True)

    undine_settings.SCHEMA = create_schema(query_class=Query)

    team = TeamFactory.create(name="team")
    project = ProjectFactory.create(name="project", team=team)
    task = TaskFactory.create(type=TaskTypeChoices.STORY.value, project=project)
    CommentFactory.create(contents="foo", target=task)
    CommentFactory.create(contents="bar", target=project)

    query = """
        query {
          comments {
            target {
              ... on ProjectType {
                name
                team {
                  name
                }
              }
              ... on TaskType {
                type
                project {
                  name
                }
              }
            }
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    # TODO: Add `GenericPrefetch` when Django 5.0 is the minimum supported version.
    #  This should lower the number of queries to 3.
    # 1 query for all comments
    # 1 query for all tasks related to the comments
    # 1 query for the projects related to the tasks  # TODO: can be optimized by `GenericPrefetch`
    # 1 query for all projects related to the comments
    # 1 query for all teams related to the projects  # TODO: can be optimized by `GenericPrefetch`
    response.assert_query_count(5)

    assert response.data == {
        "comments": [
            {
                "target": {
                    "type": "STORY",
                    "project": {"name": "project"},
                },
            },
            {
                "target": {
                    "name": "project",
                    "team": {"name": "team"},
                },
            },
        ],
    }


@pytest.mark.django_db
def test_relations__same_relation_multiple_times(graphql, undine_settings):
    class PersonType(QueryType, model=Person, auto=False):
        name = Field()
        email = Field()

    class TaskType(QueryType, model=Task, auto=False):
        assignees = Field(PersonType)

    class Query:
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query_class=Query)

    person_1 = PersonFactory.create(name="foo", email="foo@example.com")
    person_2 = PersonFactory.create(name="bar", email="bar@example.com")
    TaskFactory.create(assignees=[person_1, person_2])

    query = """
        query {
          tasks {
            assignees {
              name
            }
            assignees {
              email
            }
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    # 1 query for all tasks
    # 1 query for all assignees
    response.assert_query_count(2)

    assert response.data == {
        "tasks": [
            {
                "assignees": [
                    {"name": "foo", "email": "foo@example.com"},
                    {"name": "bar", "email": "bar@example.com"},
                ],
            },
        ],
    }


@pytest.mark.django_db
def test_relations__same_related_object_selected_with_different_fields_in_same_query(graphql, undine_settings):
    class ProjectType(QueryType, model=Project, auto=False):
        name = Field()
        tasks = Field()

    class TaskType(QueryType, model=Task, auto=False):
        name = Field()
        type = Field()
        project = Field()

    class Query:
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query_class=Query)

    project = ProjectFactory.create(name="foo")
    TaskFactory.create(name="bar", type=TaskTypeChoices.BUG_FIX.value, project=project)

    # Test that both "type" and "name" are fetched for tasks in the same query,
    # since they belong to the same object.
    query = """
        query {
          tasks {
            type
            project {
              name
              tasks {
                name
              }
            }
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    # 1 query for all tasks
    # 1 query for all assignees
    response.assert_query_count(2)

    assert response.data == {
        "tasks": [
            {
                "type": "BUG_FIX",
                "project": {
                    "name": "foo",
                    "tasks": [
                        {"name": "bar"},
                    ],
                },
            },
        ],
    }


@pytest.mark.django_db
def test_relations__related_objects_shared_by_multiple_objects(graphql, undine_settings):
    class PersonType(QueryType, model=Person, auto=False):
        name = Field()

    class ProjectType(QueryType, model=Project, auto=False):
        name = Field()

    class TaskType(QueryType, model=Task, auto=False):
        name = Field()
        project = Field(ProjectType)
        assignees = Field(PersonType)

    class Query:
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query_class=Query)

    person = PersonFactory.create(name="foo")
    project = ProjectFactory.create(name="bar")
    TaskFactory.create(name="bar", assignees=[person], project=project)
    TaskFactory.create(name="baz", assignees=[person], project=project)

    query = """
        query {
          tasks {
            name
            project {
              name
            }
            assignees {
              name
            }
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    # 1 query for all tasks and related projects
    # 1 query for all assignees
    response.assert_query_count(2)

    assert response.data == {
        "tasks": [
            {
                "name": "bar",
                "project": {"name": "bar"},
                "assignees": [{"name": "foo"}],
            },
            {
                "name": "baz",
                "project": {"name": "bar"},
                "assignees": [{"name": "foo"}],
            },
        ],
    }


@pytest.mark.django_db
def test_relations__max_query_complexity(graphql, undine_settings):
    undine_settings.OPTIMIZER_MAX_COMPLEXITY = 5

    class ProjectType(QueryType, model=Project, auto=False):
        name = Field()
        tasks = Field()

    class TaskType(QueryType, model=Task, auto=False):
        name = Field()
        project = Field(ProjectType)

    class Query:
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query_class=Query)

    project = ProjectFactory.create(name="foo")
    TaskFactory.create(name="bar", project=project)
    TaskFactory.create(name="baz", project=project)
    TaskFactory.create(name="buzz", project=project)

    query = """
        query {
          tasks {
            project {
              tasks {
                project {
                  tasks {
                    project {
                      tasks {
                        name
                      }
                    }
                  }
                }
              }
            }
          }
        }
    """

    response = graphql(query)
    assert response.error_message() == "Query complexity exceeds the maximum allowed of 5"
