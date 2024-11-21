from typing import Any

from django.contrib.auth.models import User
from factory import faker

from ._base import GenericDjangoModelFactory


class UserFactory(GenericDjangoModelFactory[User]):
    class Meta:
        model = User

    first_name = faker.Faker("first_name")
    last_name = faker.Faker("last_name")
    email = faker.Faker("email")

    @classmethod
    def create_superuser(cls, **kwargs: Any) -> User:
        kwargs["is_staff"] = True
        kwargs["is_superuser"] = True
        kwargs["is_active"] = True
        return cls.create(**kwargs)
