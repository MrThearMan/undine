import datetime

import factory
from factory import fuzzy

from example_project.app.models import ServiceRequest

from ._base import GenericDjangoModelFactory, ReverseOneToOneFactory


class ServiceRequestFactory(GenericDjangoModelFactory[ServiceRequest]):
    class Meta:
        model = ServiceRequest

    details = fuzzy.FuzzyText(length=100)
    created_at = factory.LazyFunction(datetime.datetime.now)

    task = ReverseOneToOneFactory("tests.factories.TaskFactory")
