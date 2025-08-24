from __future__ import annotations

import pytest

from example_project.app.models import Comment, Person, Project, Task, TaskTypeChoices, Team
from example_project.example.models import (
    Example,
    ExampleFFK,
    ExampleFMTM,
    ExampleFOTO,
    ExampleGeneric,
    ExampleRFK,
    ExampleRMTM,
    ExampleROTO,
    NestedExampleFFK,
    NestedExampleFMTM,
    NestedExampleFOTO,
    NestedExampleRFK,
    NestedExampleRMTM,
    NestedExampleROTO,
)
from tests.factories import CommentFactory, PersonFactory, ProjectFactory, TaskFactory, TeamFactory
from tests.factories.example import ExampleFactory
from undine import Entrypoint, Field, QueryType, RootType, create_schema

###############################################################################################


def example_schema() -> None:
    class ExampleGenericType(QueryType[ExampleGeneric]):
        @Field
        def content_type(self: ExampleGeneric) -> int:
            return self.content_type.pk  # pragma: no cover

    class ExampleType(QueryType[Example]): ...

    class ExampleFOTOType(QueryType[ExampleFOTO]): ...

    class ExampleFFKType(QueryType[ExampleFFK]): ...

    class ExampleFMTMType(QueryType[ExampleFMTM]): ...

    class ExampleROTOType(QueryType[ExampleROTO]): ...

    class ExampleRFKType(QueryType[ExampleRFK]): ...

    class ExampleRMTMType(QueryType[ExampleRMTM]): ...

    class NestedExampleFOTOType(QueryType[NestedExampleFOTO]): ...

    class NestedExampleFFKType(QueryType[NestedExampleFFK]): ...

    class NestedExampleFMTMType(QueryType[NestedExampleFMTM]): ...

    class NestedExampleROTOType(QueryType[NestedExampleROTO]): ...

    class NestedExampleRFKType(QueryType[NestedExampleRFK]): ...

    class NestedExampleRMTMType(QueryType[NestedExampleRMTM]): ...

    class Query(RootType):
        examples = Entrypoint(ExampleType, many=True)

    return create_schema(query=Query)


@pytest.mark.django_db
def test_optimizer__relations__forward_one_to_one__forward_one_to_one(graphql, undine_settings) -> None:
    undine_settings.SCHEMA = example_schema()

    ExampleFactory.create(example_foto__example_foto__name="1")
    ExampleFactory.create(example_foto__example_foto__name="2")
    ExampleFactory.create(example_foto__example_foto__name="3")

    query = """
        query {
          examples {
            exampleFoto {
              exampleFoto {
                name
              }
            }
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    response.assert_query_count(1)

    assert response.results == [
        {"exampleFoto": {"exampleFoto": {"name": "1"}}},
        {"exampleFoto": {"exampleFoto": {"name": "2"}}},
        {"exampleFoto": {"exampleFoto": {"name": "3"}}},
    ]


@pytest.mark.django_db
def test_optimizer__relations__forward_one_to_one__forward_many_to_one(graphql, undine_settings) -> None:
    undine_settings.SCHEMA = example_schema()

    ExampleFactory.create(example_foto__example_ffk__name="1")
    ExampleFactory.create(example_foto__example_ffk__name="2")
    ExampleFactory.create(example_foto__example_ffk__name="3")

    query = """
        query {
          examples {
            exampleFoto {
              exampleFfk {
                name
              }
            }
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    response.assert_query_count(1)

    assert response.results == [
        {"exampleFoto": {"exampleFfk": {"name": "1"}}},
        {"exampleFoto": {"exampleFfk": {"name": "2"}}},
        {"exampleFoto": {"exampleFfk": {"name": "3"}}},
    ]


@pytest.mark.django_db
def test_optimizer__relations__forward_one_to_one__forward_many_to_many(graphql, undine_settings) -> None:
    undine_settings.SCHEMA = example_schema()

    ExampleFactory.create(example_foto__example_fmtm_set__name="1")
    ExampleFactory.create(example_foto__example_fmtm_set__name="2")
    ExampleFactory.create(example_foto__example_fmtm_set__name="3")

    query = """
        query {
          examples {
            exampleFoto {
              exampleFmtmSet {
                name
              }
            }
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    response.assert_query_count(2)

    assert response.results == [
        {"exampleFoto": {"exampleFmtmSet": [{"name": "1"}]}},
        {"exampleFoto": {"exampleFmtmSet": [{"name": "2"}]}},
        {"exampleFoto": {"exampleFmtmSet": [{"name": "3"}]}},
    ]


@pytest.mark.django_db
def test_optimizer__relations__forward_one_to_one__reverse_one_to_one(graphql, undine_settings) -> None:
    undine_settings.SCHEMA = example_schema()

    ExampleFactory.create(example_foto__example_roto__name="1")
    ExampleFactory.create(example_foto__example_roto__name="2")
    ExampleFactory.create(example_foto__example_roto__name="3")

    query = """
        query {
          examples {
            exampleFoto {
              exampleRoto {
                name
              }
            }
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    response.assert_query_count(1)

    assert response.results == [
        {"exampleFoto": {"exampleRoto": {"name": "1"}}},
        {"exampleFoto": {"exampleRoto": {"name": "2"}}},
        {"exampleFoto": {"exampleRoto": {"name": "3"}}},
    ]


@pytest.mark.django_db
def test_optimizer__relations__forward_one_to_one__reverse_one_to_many(graphql, undine_settings) -> None:
    undine_settings.SCHEMA = example_schema()

    ExampleFactory.create(example_foto__example_rfk_set__name="1")
    ExampleFactory.create(example_foto__example_rfk_set__name="2")
    ExampleFactory.create(example_foto__example_rfk_set__name="3")

    query = """
        query {
          examples {
            exampleFoto {
              exampleRfkSet {
                name
              }
            }
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    response.assert_query_count(2)

    assert response.results == [
        {"exampleFoto": {"exampleRfkSet": [{"name": "1"}]}},
        {"exampleFoto": {"exampleRfkSet": [{"name": "2"}]}},
        {"exampleFoto": {"exampleRfkSet": [{"name": "3"}]}},
    ]


@pytest.mark.django_db
def test_optimizer__relations__forward_one_to_one__reverse_many_to_many(graphql, undine_settings) -> None:
    undine_settings.SCHEMA = example_schema()

    ExampleFactory.create(example_foto__example_rmtm_set__name="1")
    ExampleFactory.create(example_foto__example_rmtm_set__name="2")
    ExampleFactory.create(example_foto__example_rmtm_set__name="3")

    query = """
        query {
          examples {
            exampleFoto {
              exampleRmtmSet {
                name
              }
            }
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    response.assert_query_count(2)

    assert response.results == [
        {"exampleFoto": {"exampleRmtmSet": [{"name": "1"}]}},
        {"exampleFoto": {"exampleRmtmSet": [{"name": "2"}]}},
        {"exampleFoto": {"exampleRmtmSet": [{"name": "3"}]}},
    ]


###############################################################################################


@pytest.mark.django_db
def test_optimizer__relations__forward_many_to_one__forward_one_to_one(graphql, undine_settings) -> None:
    undine_settings.SCHEMA = example_schema()

    ExampleFactory.create(example_ffk__example_foto__name="1")
    ExampleFactory.create(example_ffk__example_foto__name="2")
    ExampleFactory.create(example_ffk__example_foto__name="3")

    query = """
        query {
          examples {
            exampleFfk {
              exampleFoto {
                name
              }
            }
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    response.assert_query_count(1)

    assert response.results == [
        {"exampleFfk": {"exampleFoto": {"name": "1"}}},
        {"exampleFfk": {"exampleFoto": {"name": "2"}}},
        {"exampleFfk": {"exampleFoto": {"name": "3"}}},
    ]


@pytest.mark.django_db
def test_optimizer__relations__forward_many_to_one__forward_many_to_one(graphql, undine_settings) -> None:
    undine_settings.SCHEMA = example_schema()

    ExampleFactory.create(example_ffk__example_ffk__name="1")
    ExampleFactory.create(example_ffk__example_ffk__name="2")
    ExampleFactory.create(example_ffk__example_ffk__name="3")

    query = """
        query {
          examples {
            exampleFfk {
              exampleFfk {
                name
              }
            }
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    response.assert_query_count(1)

    assert response.results == [
        {"exampleFfk": {"exampleFfk": {"name": "1"}}},
        {"exampleFfk": {"exampleFfk": {"name": "2"}}},
        {"exampleFfk": {"exampleFfk": {"name": "3"}}},
    ]


@pytest.mark.django_db
def test_optimizer__relations__forward_many_to_one__forward_many_to_many(graphql, undine_settings) -> None:
    undine_settings.SCHEMA = example_schema()

    ExampleFactory.create(example_ffk__example_fmtm_set__name="1")
    ExampleFactory.create(example_ffk__example_fmtm_set__name="2")
    ExampleFactory.create(example_ffk__example_fmtm_set__name="3")

    query = """
        query {
          examples {
            exampleFfk {
              exampleFmtmSet {
                name
              }
            }
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    response.assert_query_count(2)

    assert response.results == [
        {"exampleFfk": {"exampleFmtmSet": [{"name": "1"}]}},
        {"exampleFfk": {"exampleFmtmSet": [{"name": "2"}]}},
        {"exampleFfk": {"exampleFmtmSet": [{"name": "3"}]}},
    ]


@pytest.mark.django_db
def test_optimizer__relations__forward_many_to_one__reverse_one_to_one(graphql, undine_settings) -> None:
    undine_settings.SCHEMA = example_schema()

    ExampleFactory.create(example_ffk__example_roto__name="1")
    ExampleFactory.create(example_ffk__example_roto__name="2")
    ExampleFactory.create(example_ffk__example_roto__name="3")

    query = """
        query {
          examples {
            exampleFfk {
              exampleRoto {
                name
              }
            }
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    response.assert_query_count(1)

    assert response.results == [
        {"exampleFfk": {"exampleRoto": {"name": "1"}}},
        {"exampleFfk": {"exampleRoto": {"name": "2"}}},
        {"exampleFfk": {"exampleRoto": {"name": "3"}}},
    ]


@pytest.mark.django_db
def test_optimizer__relations__forward_many_to_one__reverse_one_to_many(graphql, undine_settings) -> None:
    undine_settings.SCHEMA = example_schema()

    ExampleFactory.create(example_ffk__example_rfk_set__name="1")
    ExampleFactory.create(example_ffk__example_rfk_set__name="2")
    ExampleFactory.create(example_ffk__example_rfk_set__name="3")

    query = """
        query {
          examples {
            exampleFfk {
              exampleRfkSet {
                name
              }
            }
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    response.assert_query_count(2)

    assert response.results == [
        {"exampleFfk": {"exampleRfkSet": [{"name": "1"}]}},
        {"exampleFfk": {"exampleRfkSet": [{"name": "2"}]}},
        {"exampleFfk": {"exampleRfkSet": [{"name": "3"}]}},
    ]


@pytest.mark.django_db
def test_optimizer__relations__forward_many_to_one__reverse_many_to_many(graphql, undine_settings) -> None:
    undine_settings.SCHEMA = example_schema()

    ExampleFactory.create(example_ffk__example_rmtm_set__name="1")
    ExampleFactory.create(example_ffk__example_rmtm_set__name="2")
    ExampleFactory.create(example_ffk__example_rmtm_set__name="3")

    query = """
        query {
          examples {
            exampleFfk {
              exampleRmtmSet {
                name
              }
            }
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    response.assert_query_count(2)

    assert response.results == [
        {"exampleFfk": {"exampleRmtmSet": [{"name": "1"}]}},
        {"exampleFfk": {"exampleRmtmSet": [{"name": "2"}]}},
        {"exampleFfk": {"exampleRmtmSet": [{"name": "3"}]}},
    ]


###############################################################################################


@pytest.mark.django_db
def test_optimizer__relations__forward_many_to_many__forward_one_to_one(graphql, undine_settings) -> None:
    undine_settings.SCHEMA = example_schema()

    ExampleFactory.create(example_fmtm_set__example_foto__name="1")
    ExampleFactory.create(example_fmtm_set__example_foto__name="2")
    ExampleFactory.create(example_fmtm_set__example_foto__name="3")

    query = """
        query {
          examples {
            exampleFmtmSet {
              exampleFoto {
                name
              }
            }
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    response.assert_query_count(2)

    assert response.results == [
        {"exampleFmtmSet": [{"exampleFoto": {"name": "1"}}]},
        {"exampleFmtmSet": [{"exampleFoto": {"name": "2"}}]},
        {"exampleFmtmSet": [{"exampleFoto": {"name": "3"}}]},
    ]


@pytest.mark.django_db
def test_optimizer__relations__forward_many_to_many__forward_many_to_one(graphql, undine_settings) -> None:
    undine_settings.SCHEMA = example_schema()

    ExampleFactory.create(example_fmtm_set__example_ffk__name="1")
    ExampleFactory.create(example_fmtm_set__example_ffk__name="2")
    ExampleFactory.create(example_fmtm_set__example_ffk__name="3")

    query = """
        query {
          examples {
            exampleFmtmSet {
              exampleFfk {
                name
              }
            }
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    response.assert_query_count(2)

    assert response.results == [
        {"exampleFmtmSet": [{"exampleFfk": {"name": "1"}}]},
        {"exampleFmtmSet": [{"exampleFfk": {"name": "2"}}]},
        {"exampleFmtmSet": [{"exampleFfk": {"name": "3"}}]},
    ]


@pytest.mark.django_db
def test_optimizer__relations__forward_many_to_many__forward_many_to_many(graphql, undine_settings) -> None:
    undine_settings.SCHEMA = example_schema()

    ExampleFactory.create(example_fmtm_set__example_fmtm_set__name="1")
    ExampleFactory.create(example_fmtm_set__example_fmtm_set__name="2")
    ExampleFactory.create(example_fmtm_set__example_fmtm_set__name="3")

    query = """
        query {
          examples {
            exampleFmtmSet {
              exampleFmtmSet {
                name
              }
            }
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    response.assert_query_count(3)

    assert response.results == [
        {"exampleFmtmSet": [{"exampleFmtmSet": [{"name": "1"}]}]},
        {"exampleFmtmSet": [{"exampleFmtmSet": [{"name": "2"}]}]},
        {"exampleFmtmSet": [{"exampleFmtmSet": [{"name": "3"}]}]},
    ]


@pytest.mark.django_db
def test_optimizer__relations__forward_many_to_many__reverse_one_to_one(graphql, undine_settings) -> None:
    undine_settings.SCHEMA = example_schema()

    ExampleFactory.create(example_fmtm_set__example_roto__name="1")
    ExampleFactory.create(example_fmtm_set__example_roto__name="2")
    ExampleFactory.create(example_fmtm_set__example_roto__name="3")

    query = """
        query {
          examples {
            exampleFmtmSet {
              exampleRoto {
                name
              }
            }
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    response.assert_query_count(2)

    assert response.results == [
        {"exampleFmtmSet": [{"exampleRoto": {"name": "1"}}]},
        {"exampleFmtmSet": [{"exampleRoto": {"name": "2"}}]},
        {"exampleFmtmSet": [{"exampleRoto": {"name": "3"}}]},
    ]


@pytest.mark.django_db
def test_optimizer__relations__forward_many_to_many__reverse_one_to_many(graphql, undine_settings) -> None:
    undine_settings.SCHEMA = example_schema()

    ExampleFactory.create(example_fmtm_set__example_rfk_set__name="1")
    ExampleFactory.create(example_fmtm_set__example_rfk_set__name="2")
    ExampleFactory.create(example_fmtm_set__example_rfk_set__name="3")

    query = """
        query {
          examples {
            exampleFmtmSet {
              exampleRfkSet {
                name
              }
            }
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    response.assert_query_count(3)

    assert response.results == [
        {"exampleFmtmSet": [{"exampleRfkSet": [{"name": "1"}]}]},
        {"exampleFmtmSet": [{"exampleRfkSet": [{"name": "2"}]}]},
        {"exampleFmtmSet": [{"exampleRfkSet": [{"name": "3"}]}]},
    ]


@pytest.mark.django_db
def test_optimizer__relations__forward_many_to_many__reverse_many_to_many(graphql, undine_settings) -> None:
    undine_settings.SCHEMA = example_schema()

    ExampleFactory.create(example_fmtm_set__example_rmtm_set__name="1")
    ExampleFactory.create(example_fmtm_set__example_rmtm_set__name="2")
    ExampleFactory.create(example_fmtm_set__example_rmtm_set__name="3")

    query = """
        query {
          examples {
            exampleFmtmSet {
              exampleRmtmSet {
                name
              }
            }
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    response.assert_query_count(3)

    assert response.results == [
        {"exampleFmtmSet": [{"exampleRmtmSet": [{"name": "1"}]}]},
        {"exampleFmtmSet": [{"exampleRmtmSet": [{"name": "2"}]}]},
        {"exampleFmtmSet": [{"exampleRmtmSet": [{"name": "3"}]}]},
    ]


###############################################################################################


@pytest.mark.django_db
def test_optimizer__relations__reverse_one_to_one__forward_one_to_one(graphql, undine_settings) -> None:
    undine_settings.SCHEMA = example_schema()

    ExampleFactory.create(example_roto__example_foto__name="1")
    ExampleFactory.create(example_roto__example_foto__name="2")
    ExampleFactory.create(example_roto__example_foto__name="3")

    query = """
        query {
          examples {
            exampleRoto {
              exampleFoto {
                name
              }
            }
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    response.assert_query_count(1)

    assert response.results == [
        {"exampleRoto": {"exampleFoto": {"name": "1"}}},
        {"exampleRoto": {"exampleFoto": {"name": "2"}}},
        {"exampleRoto": {"exampleFoto": {"name": "3"}}},
    ]


@pytest.mark.django_db
def test_optimizer__relations__reverse_one_to_one__forward_many_to_one(graphql, undine_settings) -> None:
    undine_settings.SCHEMA = example_schema()

    ExampleFactory.create(example_roto__example_ffk__name="1")
    ExampleFactory.create(example_roto__example_ffk__name="2")
    ExampleFactory.create(example_roto__example_ffk__name="3")

    query = """
        query {
          examples {
            exampleRoto {
              exampleFfk {
                name
              }
            }
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    response.assert_query_count(1)

    assert response.results == [
        {"exampleRoto": {"exampleFfk": {"name": "1"}}},
        {"exampleRoto": {"exampleFfk": {"name": "2"}}},
        {"exampleRoto": {"exampleFfk": {"name": "3"}}},
    ]


@pytest.mark.django_db
def test_optimizer__relations__reverse_one_to_one__forward_many_to_many(graphql, undine_settings) -> None:
    undine_settings.SCHEMA = example_schema()

    ExampleFactory.create(example_roto__example_fmtm_set__name="1")
    ExampleFactory.create(example_roto__example_fmtm_set__name="2")
    ExampleFactory.create(example_roto__example_fmtm_set__name="3")

    query = """
        query {
          examples {
            exampleRoto {
              exampleFmtmSet {
                name
              }
            }
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    response.assert_query_count(2)

    assert response.results == [
        {"exampleRoto": {"exampleFmtmSet": [{"name": "1"}]}},
        {"exampleRoto": {"exampleFmtmSet": [{"name": "2"}]}},
        {"exampleRoto": {"exampleFmtmSet": [{"name": "3"}]}},
    ]


@pytest.mark.django_db
def test_optimizer__relations__reverse_one_to_one__reverse_one_to_one(graphql, undine_settings) -> None:
    undine_settings.SCHEMA = example_schema()

    ExampleFactory.create(example_roto__example_roto__name="1")
    ExampleFactory.create(example_roto__example_roto__name="2")
    ExampleFactory.create(example_roto__example_roto__name="3")

    query = """
        query {
          examples {
            exampleRoto {
              exampleRoto {
                name
              }
            }
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    response.assert_query_count(1)

    assert response.results == [
        {"exampleRoto": {"exampleRoto": {"name": "1"}}},
        {"exampleRoto": {"exampleRoto": {"name": "2"}}},
        {"exampleRoto": {"exampleRoto": {"name": "3"}}},
    ]


@pytest.mark.django_db
def test_optimizer__relations__reverse_one_to_one__reverse_one_to_many(graphql, undine_settings) -> None:
    undine_settings.SCHEMA = example_schema()

    ExampleFactory.create(example_roto__example_rfk_set__name="1")
    ExampleFactory.create(example_roto__example_rfk_set__name="2")
    ExampleFactory.create(example_roto__example_rfk_set__name="3")

    query = """
        query {
          examples {
            exampleRoto {
              exampleRfkSet {
                name
              }
            }
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    response.assert_query_count(2)

    assert response.results == [
        {"exampleRoto": {"exampleRfkSet": [{"name": "1"}]}},
        {"exampleRoto": {"exampleRfkSet": [{"name": "2"}]}},
        {"exampleRoto": {"exampleRfkSet": [{"name": "3"}]}},
    ]


@pytest.mark.django_db
def test_optimizer__relations__reverse_one_to_one__reverse_many_to_many(graphql, undine_settings) -> None:
    undine_settings.SCHEMA = example_schema()

    ExampleFactory.create(example_roto__example_rmtm_set__name="1")
    ExampleFactory.create(example_roto__example_rmtm_set__name="2")
    ExampleFactory.create(example_roto__example_rmtm_set__name="3")

    query = """
        query {
          examples {
            exampleRoto {
              exampleRmtmSet {
                name
              }
            }
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    response.assert_query_count(2)

    assert response.results == [
        {"exampleRoto": {"exampleRmtmSet": [{"name": "1"}]}},
        {"exampleRoto": {"exampleRmtmSet": [{"name": "2"}]}},
        {"exampleRoto": {"exampleRmtmSet": [{"name": "3"}]}},
    ]


###############################################################################################


@pytest.mark.django_db
def test_optimizer__relations__reverse_one_to_many__forward_one_to_one(graphql, undine_settings) -> None:
    undine_settings.SCHEMA = example_schema()

    ExampleFactory.create(example_rfk_set__example_foto__name="1")
    ExampleFactory.create(example_rfk_set__example_foto__name="2")
    ExampleFactory.create(example_rfk_set__example_foto__name="3")

    query = """
        query {
          examples {
            exampleRfkSet {
              exampleFoto {
                name
              }
            }
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    response.assert_query_count(2)

    assert response.results == [
        {"exampleRfkSet": [{"exampleFoto": {"name": "1"}}]},
        {"exampleRfkSet": [{"exampleFoto": {"name": "2"}}]},
        {"exampleRfkSet": [{"exampleFoto": {"name": "3"}}]},
    ]


@pytest.mark.django_db
def test_optimizer__relations__reverse_one_to_many__forward_many_to_one(graphql, undine_settings) -> None:
    undine_settings.SCHEMA = example_schema()

    ExampleFactory.create(example_rfk_set__example_ffk__name="1")
    ExampleFactory.create(example_rfk_set__example_ffk__name="2")
    ExampleFactory.create(example_rfk_set__example_ffk__name="3")

    query = """
        query {
          examples {
            exampleRfkSet {
              exampleFfk {
                name
              }
            }
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    response.assert_query_count(2)

    assert response.results == [
        {"exampleRfkSet": [{"exampleFfk": {"name": "1"}}]},
        {"exampleRfkSet": [{"exampleFfk": {"name": "2"}}]},
        {"exampleRfkSet": [{"exampleFfk": {"name": "3"}}]},
    ]


@pytest.mark.django_db
def test_optimizer__relations__reverse_one_to_many__forward_many_to_many(graphql, undine_settings) -> None:
    undine_settings.SCHEMA = example_schema()

    ExampleFactory.create(example_rfk_set__example_fmtm_set__name="1")
    ExampleFactory.create(example_rfk_set__example_fmtm_set__name="2")
    ExampleFactory.create(example_rfk_set__example_fmtm_set__name="3")

    query = """
        query {
          examples {
            exampleRfkSet {
              exampleFmtmSet {
                name
              }
            }
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    response.assert_query_count(3)

    assert response.results == [
        {"exampleRfkSet": [{"exampleFmtmSet": [{"name": "1"}]}]},
        {"exampleRfkSet": [{"exampleFmtmSet": [{"name": "2"}]}]},
        {"exampleRfkSet": [{"exampleFmtmSet": [{"name": "3"}]}]},
    ]


@pytest.mark.django_db
def test_optimizer__relations__reverse_one_to_many__reverse_one_to_one(graphql, undine_settings) -> None:
    undine_settings.SCHEMA = example_schema()

    ExampleFactory.create(example_rfk_set__example_roto__name="1")
    ExampleFactory.create(example_rfk_set__example_roto__name="2")
    ExampleFactory.create(example_rfk_set__example_roto__name="3")

    query = """
        query {
          examples {
            exampleRfkSet {
              exampleRoto {
                name
              }
            }
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    response.assert_query_count(2)

    assert response.results == [
        {"exampleRfkSet": [{"exampleRoto": {"name": "1"}}]},
        {"exampleRfkSet": [{"exampleRoto": {"name": "2"}}]},
        {"exampleRfkSet": [{"exampleRoto": {"name": "3"}}]},
    ]


@pytest.mark.django_db
def test_optimizer__relations__reverse_one_to_many__reverse_one_to_many(graphql, undine_settings) -> None:
    undine_settings.SCHEMA = example_schema()

    ExampleFactory.create(example_rfk_set__example_rfk_set__name="1")
    ExampleFactory.create(example_rfk_set__example_rfk_set__name="2")
    ExampleFactory.create(example_rfk_set__example_rfk_set__name="3")

    query = """
        query {
          examples {
            exampleRfkSet {
              exampleRfkSet {
                name
              }
            }
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    response.assert_query_count(3)

    assert response.results == [
        {"exampleRfkSet": [{"exampleRfkSet": [{"name": "1"}]}]},
        {"exampleRfkSet": [{"exampleRfkSet": [{"name": "2"}]}]},
        {"exampleRfkSet": [{"exampleRfkSet": [{"name": "3"}]}]},
    ]


@pytest.mark.django_db
def test_optimizer__relations__reverse_one_to_many__reverse_many_to_many(graphql, undine_settings) -> None:
    undine_settings.SCHEMA = example_schema()

    ExampleFactory.create(example_rfk_set__example_rmtm_set__name="1")
    ExampleFactory.create(example_rfk_set__example_rmtm_set__name="2")
    ExampleFactory.create(example_rfk_set__example_rmtm_set__name="3")

    query = """
        query {
          examples {
            exampleRfkSet {
              exampleRmtmSet {
                name
              }
            }
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    response.assert_query_count(3)

    assert response.results == [
        {"exampleRfkSet": [{"exampleRmtmSet": [{"name": "1"}]}]},
        {"exampleRfkSet": [{"exampleRmtmSet": [{"name": "2"}]}]},
        {"exampleRfkSet": [{"exampleRmtmSet": [{"name": "3"}]}]},
    ]


###############################################################################################


@pytest.mark.django_db
def test_optimizer__relations__reverse_many_to_many__forward_one_to_one(graphql, undine_settings) -> None:
    undine_settings.SCHEMA = example_schema()

    ExampleFactory.create(example_rmtm_set__example_foto__name="1")
    ExampleFactory.create(example_rmtm_set__example_foto__name="2")
    ExampleFactory.create(example_rmtm_set__example_foto__name="3")

    query = """
        query {
          examples {
            exampleRmtmSet {
              exampleFoto {
                name
              }
            }
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    response.assert_query_count(2)

    assert response.results == [
        {"exampleRmtmSet": [{"exampleFoto": {"name": "1"}}]},
        {"exampleRmtmSet": [{"exampleFoto": {"name": "2"}}]},
        {"exampleRmtmSet": [{"exampleFoto": {"name": "3"}}]},
    ]


@pytest.mark.django_db
def test_optimizer__relations__reverse_many_to_many__forward_many_to_one(graphql, undine_settings) -> None:
    undine_settings.SCHEMA = example_schema()

    ExampleFactory.create(example_rmtm_set__example_ffk__name="1")
    ExampleFactory.create(example_rmtm_set__example_ffk__name="2")
    ExampleFactory.create(example_rmtm_set__example_ffk__name="3")

    query = """
        query {
          examples {
            exampleRmtmSet {
              exampleFfk {
                name
              }
            }
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    response.assert_query_count(2)

    assert response.results == [
        {"exampleRmtmSet": [{"exampleFfk": {"name": "1"}}]},
        {"exampleRmtmSet": [{"exampleFfk": {"name": "2"}}]},
        {"exampleRmtmSet": [{"exampleFfk": {"name": "3"}}]},
    ]


@pytest.mark.django_db
def test_optimizer__relations__reverse_many_to_many__forward_many_to_many(graphql, undine_settings) -> None:
    undine_settings.SCHEMA = example_schema()

    ExampleFactory.create(example_rmtm_set__example_fmtm_set__name="1")
    ExampleFactory.create(example_rmtm_set__example_fmtm_set__name="2")
    ExampleFactory.create(example_rmtm_set__example_fmtm_set__name="3")

    query = """
        query {
          examples {
            exampleRmtmSet {
              exampleFmtmSet {
                name
              }
            }
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    response.assert_query_count(3)

    assert response.results == [
        {"exampleRmtmSet": [{"exampleFmtmSet": [{"name": "1"}]}]},
        {"exampleRmtmSet": [{"exampleFmtmSet": [{"name": "2"}]}]},
        {"exampleRmtmSet": [{"exampleFmtmSet": [{"name": "3"}]}]},
    ]


@pytest.mark.django_db
def test_optimizer__relations__reverse_many_to_many__reverse_one_to_one(graphql, undine_settings) -> None:
    undine_settings.SCHEMA = example_schema()

    ExampleFactory.create(example_rmtm_set__example_roto__name="1")
    ExampleFactory.create(example_rmtm_set__example_roto__name="2")
    ExampleFactory.create(example_rmtm_set__example_roto__name="3")

    query = """
        query {
          examples {
            exampleRmtmSet {
              exampleRoto {
                name
              }
            }
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    response.assert_query_count(2)

    assert response.results == [
        {"exampleRmtmSet": [{"exampleRoto": {"name": "1"}}]},
        {"exampleRmtmSet": [{"exampleRoto": {"name": "2"}}]},
        {"exampleRmtmSet": [{"exampleRoto": {"name": "3"}}]},
    ]


@pytest.mark.django_db
def test_optimizer__relations__reverse_many_to_many__reverse_one_to_many(graphql, undine_settings) -> None:
    undine_settings.SCHEMA = example_schema()

    ExampleFactory.create(example_rmtm_set__example_rfk_set__name="1")
    ExampleFactory.create(example_rmtm_set__example_rfk_set__name="2")
    ExampleFactory.create(example_rmtm_set__example_rfk_set__name="3")

    query = """
        query {
          examples {
            exampleRmtmSet {
              exampleRfkSet {
                name
              }
            }
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    response.assert_query_count(3)

    assert response.results == [
        {"exampleRmtmSet": [{"exampleRfkSet": [{"name": "1"}]}]},
        {"exampleRmtmSet": [{"exampleRfkSet": [{"name": "2"}]}]},
        {"exampleRmtmSet": [{"exampleRfkSet": [{"name": "3"}]}]},
    ]


@pytest.mark.django_db
def test_optimizer__relations__reverse_many_to_many__reverse_many_to_many(graphql, undine_settings) -> None:
    undine_settings.SCHEMA = example_schema()

    ExampleFactory.create(example_rmtm_set__example_rmtm_set__name="1")
    ExampleFactory.create(example_rmtm_set__example_rmtm_set__name="2")
    ExampleFactory.create(example_rmtm_set__example_rmtm_set__name="3")

    query = """
        query {
          examples {
            exampleRmtmSet {
              exampleRmtmSet {
                name
              }
            }
          }
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    response.assert_query_count(3)

    assert response.results == [
        {"exampleRmtmSet": [{"exampleRmtmSet": [{"name": "1"}]}]},
        {"exampleRmtmSet": [{"exampleRmtmSet": [{"name": "2"}]}]},
        {"exampleRmtmSet": [{"exampleRmtmSet": [{"name": "3"}]}]},
    ]


###############################################################################################


@pytest.mark.django_db
def test_optimizer__relations__generic_relation(graphql, undine_settings) -> None:
    class CommentType(QueryType[Comment], auto=False):
        contents = Field()

    class TaskType(QueryType[Task], auto=False):
        comments = Field(CommentType)

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

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
def test_optimizer__relations__generic_foreign_key(graphql, undine_settings) -> None:
    class TaskType(QueryType[Task], auto=False):
        type = Field()

    class ProjectType(QueryType[Project], auto=False):
        name = Field()

    class CommentType(QueryType[Comment], auto=False):
        target = Field()

    class Query(RootType):
        comments = Entrypoint(CommentType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

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
def test_optimizer__relations__generic_foreign_key__as_nested_relation(graphql, undine_settings) -> None:
    class TaskType(QueryType[Task], auto=False):
        type = Field()

    class ProjectType(QueryType[Project], auto=False):
        name = Field()

    class CommentType(QueryType[Comment], auto=False):
        contents = Field()
        target = Field()

    class PersonType(QueryType[Person], auto=False):
        name = Field()
        comments = Field(CommentType)

    class Query(RootType):
        people = Entrypoint(PersonType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

    task = TaskFactory.create(type=TaskTypeChoices.TASK.value)
    project = ProjectFactory.create(name="Project 1")

    person_1 = PersonFactory.create(name="Person 1")
    person_2 = PersonFactory.create(name="Person 2")

    CommentFactory.create(contents="Comment 1", target=task, commenter=person_1)
    CommentFactory.create(contents="Comment 2", target=project, commenter=person_1)
    CommentFactory.create(contents="Comment 3", target=project, commenter=person_2)

    query = """
        query {
          people {
            name
            comments {
              contents
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
        }
    """

    response = graphql(query)
    assert response.has_errors is False, response.errors

    response.assert_query_count(4)

    assert response.data == {
        "people": [
            {
                "name": "Person 1",
                "comments": [
                    {
                        "contents": "Comment 1",
                        "target": {"type": "TASK"},
                    },
                    {
                        "contents": "Comment 2",
                        "target": {"name": "Project 1"},
                    },
                ],
            },
            {
                "name": "Person 2",
                "comments": [
                    {
                        "contents": "Comment 3",
                        "target": {"name": "Project 1"},
                    },
                ],
            },
        ],
    }


@pytest.mark.django_db
def test_optimizer__relations__generic_foreign_key__with_nested_relations(graphql, undine_settings) -> None:
    class TeamType(QueryType[Team], auto=False):
        name = Field()

    class ProjectType(QueryType[Project], auto=False):
        name = Field()
        team = Field(TeamType)

    class TaskType(QueryType[Task], auto=False):
        type = Field()
        project = Field(ProjectType)

    class CommentType(QueryType[Comment], auto=False):
        target = Field()

    class Query(RootType):
        comments = Entrypoint(CommentType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

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

    response.assert_query_count(3)

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
def test_optimizer__relations__same_relation_multiple_times(graphql, undine_settings) -> None:
    class PersonType(QueryType[Person], auto=False):
        name = Field()
        email = Field()

    class TaskType(QueryType[Task], auto=False):
        assignees = Field(PersonType)

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

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
def test_optimizer__relations__same_related_object_selected_with_different_fields(graphql, undine_settings) -> None:
    class ProjectType(QueryType[Project], auto=False):
        name = Field()
        tasks = Field()

    class TaskType(QueryType[Task], auto=False):
        name = Field()
        type = Field()
        project = Field()

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

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
def test_optimizer__relations__related_objects_shared_by_multiple_objects(graphql, undine_settings) -> None:
    class PersonType(QueryType[Person], auto=False):
        name = Field()

    class ProjectType(QueryType[Project], auto=False):
        name = Field()

    class TaskType(QueryType[Task], auto=False):
        name = Field()
        project = Field(ProjectType)
        assignees = Field(PersonType)

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

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
def test_optimizer__relations__max_query_complexity(graphql, undine_settings) -> None:
    undine_settings.MAX_QUERY_COMPLEXITY = 5

    class ProjectType(QueryType[Project], auto=False):
        name = Field()
        tasks = Field()

    class TaskType(QueryType[Task], auto=False):
        name = Field()
        project = Field(ProjectType)

    class Query(RootType):
        tasks = Entrypoint(TaskType, many=True)

    undine_settings.SCHEMA = create_schema(query=Query)

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
    assert response.error_message(0) == "Query complexity of 6 exceeds the maximum allowed complexity of 5."
