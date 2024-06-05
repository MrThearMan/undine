from __future__ import annotations

from typing import Any

from django.contrib.auth.models import User

from ._base import GenericDjangoModelFactory, UndineFaker


class UserFactory(GenericDjangoModelFactory[User]):
    class Meta:
        model = User

    first_name = UndineFaker("first_name")
    last_name = UndineFaker("last_name")
    email = UndineFaker("email")

    @classmethod
    def create_superuser(cls, **kwargs: Any) -> User:  # pragma: no cover
        kwargs["is_staff"] = True
        kwargs["is_superuser"] = True
        kwargs["is_active"] = True
        return cls.create(**kwargs)
