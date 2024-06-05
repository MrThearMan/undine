from django.contrib import admin

from .models import (
    Example,
    ForwardManyToMany,
    ForwardManyToOne,
    ForwardOneToOne,
    ReverseManyToMany,
    ReverseOneToMany,
    ReverseOneToOne,
)


@admin.register(Example)
class ExampleAdmin(admin.ModelAdmin): ...


@admin.register(ForwardManyToMany)
class ForwardManyToManyAdmin(admin.ModelAdmin): ...


@admin.register(ForwardManyToOne)
class ForwardManyToOneAdmin(admin.ModelAdmin): ...


@admin.register(ForwardOneToOne)
class ForwardOneToOneAdmin(admin.ModelAdmin): ...


@admin.register(ReverseManyToMany)
class ReverseManyToManyAdmin(admin.ModelAdmin): ...


@admin.register(ReverseOneToOne)
class ReverseManyToManyAdmin(admin.ModelAdmin): ...


@admin.register(ReverseOneToMany)
class ReverseOneToManyAdmin(admin.ModelAdmin): ...
