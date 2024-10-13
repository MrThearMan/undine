from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable, Generic, TypeVar, Union

from django.contrib.contenttypes.fields import GenericForeignKey
from django.db.models import Model
from factory import FactoryError, PostGeneration
from factory.base import BaseFactory
from factory.declarations import SubFactory
from factory.django import DjangoModelFactory
from factory.utils import import_object

if TYPE_CHECKING:
    from collections.abc import Iterable

    from factory.builder import BuildStep, Resolver


FactoryType = Union[str, type[BaseFactory], Callable[[], type[BaseFactory]]]
TModel = TypeVar("TModel", bound=Model)


__all__ = [
    "GenericDjangoModelFactory",
    "ManyToManyFactory",
    "NullableSubFactory",
    "OneToManyFactory",
]


class GenericDjangoModelFactory(DjangoModelFactory, Generic[TModel]):
    @classmethod
    def build(cls: type[Generic[TModel]], **kwargs: Any) -> TModel:
        return super().build(**kwargs)

    @classmethod
    def create(cls: type[Generic[TModel]], **kwargs: Any) -> TModel:
        return super().create(**kwargs)

    @classmethod
    def build_batch(cls: type[Generic[TModel]], size: int, **kwargs: Any) -> list[TModel]:
        return super().build_batch(size, **kwargs)

    @classmethod
    def create_batch(cls: type[Generic[TModel]], size: int, **kwargs: Any) -> list[TModel]:
        return super().create_batch(size, **kwargs)


class CustomFactoryWrapper:
    def __init__(self, factory_: FactoryType) -> None:
        self.factory: type[BaseFactory] | None = None
        self.callable: Callable[..., type[BaseFactory]] | None = None

        if isinstance(factory_, type) and issubclass(factory_, BaseFactory):
            self.factory = factory_
            return

        if callable(factory_):
            self.callable = factory_
            return

        if not (isinstance(factory_, str) and "." in factory_):
            msg = (
                "The factory must be one of: "
                "1) a string with the format 'module.path.FactoryClass' "
                "2) a Factory class "
                "3) a callable that returns a Factory class"
            )
            raise FactoryError(msg)

        self.callable = lambda: import_object(*factory_.rsplit(".", 1))

    def get(self) -> FactoryType:
        if self.factory is None:
            self.factory = self.callable()
        return self.factory


class PostFactory(PostGeneration, Generic[TModel]):
    def __init__(self, factory: FactoryType) -> None:
        super().__init__(function=self.generate)
        self.field_name: str = ""
        self.factory_wrapper = CustomFactoryWrapper(factory)

    def __set_name__(self, owner: Any, name: str) -> None:
        self.field_name = name

    def get_factory(self) -> BaseFactory:
        return self.factory_wrapper.get()

    def generate(self, instance: Model, create: bool, models: Iterable[TModel] | None, **kwargs: Any) -> None:
        raise NotImplementedError

    def manager(self, instance: Model) -> Any:
        return getattr(instance, self.field_name)


class ManyToManyFactory(PostFactory[TModel]):
    def generate(self, instance: Model, create: bool, models: Iterable[TModel] | None, **kwargs: Any) -> None:
        if not models and kwargs:
            factory = self.get_factory()
            model = factory.create(**kwargs) if create else factory.build(**kwargs)
            self.manager(instance).add(model)

        for model in models or []:
            self.manager(instance).add(model)


class OneToManyFactory(PostFactory[TModel]):
    def generate(self, instance: Model, create: bool, models: Iterable[TModel] | None, **kwargs: Any) -> None:
        if not models and kwargs:
            factory = self.get_factory()
            manager = self.manager(instance)
            try:
                field_name = manager.field.name
            except AttributeError:
                # GenericForeignKey
                field = next(
                    field
                    for field in manager.model._meta.get_fields()
                    if (
                        isinstance(field, GenericForeignKey)
                        and field.fk_field == manager.object_id_field_name
                        and field.ct_field == manager.content_type_field_name
                    )
                )
                field_name = field.name
            kwargs.setdefault(field_name, instance)
            factory.create(**kwargs) if create else factory.build(**kwargs)


class ReverseSubFactory(PostFactory[TModel]):
    def generate(self, instance: Model, create: bool, models: Iterable[TModel] | None, **kwargs: Any) -> None:
        if not models and kwargs:
            factory = self.get_factory()
            field_name = instance._meta.get_field(self.field_name).remote_field.name
            kwargs.setdefault(field_name, instance)
            factory.create(**kwargs) if create else factory.build(**kwargs)


class NullableSubFactory(SubFactory, Generic[TModel]):
    def __init__(self, factory: FactoryType, null: bool = False, **kwargs: Any) -> None:
        # Skip SubFactory.__init__ to replace its factory wrapper with ours
        self.null = null
        super(SubFactory, self).__init__(**kwargs)
        self.factory_wrapper = CustomFactoryWrapper(factory)

    def evaluate(self, instance: Resolver, step: BuildStep, extra: dict[str, Any]) -> TModel | None:
        if not extra and self.null:
            return None
        return super().evaluate(instance, step, extra)
