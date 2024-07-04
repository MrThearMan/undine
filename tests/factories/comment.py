import datetime

import factory
from factory import SubFactory, fuzzy

from example_project.app.models import Comment

from ._base import GenericDjangoModelFactory


class CommentFactory(GenericDjangoModelFactory[Comment]):
    class Meta:
        model = Comment

    contents = fuzzy.FuzzyText(length=100)
    updated_at = factory.LazyFunction(datetime.datetime.now)

    commenter = SubFactory("tests.factories.person.PersonFactory")
