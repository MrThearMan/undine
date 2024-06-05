from __future__ import annotations

from django.db.models import CASCADE, CharField, ForeignKey, ManyToManyField, Model, OneToOneField

__all__ = [
    "Example",
    "ForwardManyToMany",
    "ForwardManyToManyForRelated",
    "ForwardManyToOne",
    "ForwardManyToOneForRelated",
    "ForwardOneToOne",
    "ForwardOneToOneForRelated",
    "ReverseManyToMany",
    "ReverseManyToManyToForwardManyToMany",
    "ReverseManyToManyToForwardManyToOne",
    "ReverseManyToManyToForwardOneToOne",
    "ReverseManyToManyToReverseManyToMany",
    "ReverseManyToManyToReverseOneToMany",
    "ReverseManyToManyToReverseOneToOne",
    "ReverseOneToMany",
    "ReverseOneToManyToForwardManyToMany",
    "ReverseOneToManyToForwardManyToOne",
    "ReverseOneToManyToForwardOneToOne",
    "ReverseOneToManyToReverseManyToMany",
    "ReverseOneToManyToReverseOneToMany",
    "ReverseOneToManyToReverseOneToOne",
    "ReverseOneToOne",
    "ReverseOneToOneToForwardManyToMany",
    "ReverseOneToOneToForwardManyToOne",
    "ReverseOneToOneToForwardOneToOne",
    "ReverseOneToOneToReverseManyToMany",
    "ReverseOneToOneToReverseOneToMany",
    "ReverseOneToOneToReverseOneToOne",
]


# --------------------------------------------------------------------


class BaseModel(Model):
    name = CharField(max_length=255)

    class Meta:
        ordering = ["pk"]
        abstract = True

    def __str__(self) -> str:
        return self.__class__.__name__ + ": " + self.name


class Example(BaseModel):
    symmetrical_field = ManyToManyField("self")
    forward_one_to_one_field = OneToOneField(
        "ForwardOneToOne",
        on_delete=CASCADE,
        related_name="example_rel",
    )
    forward_many_to_one_field = ForeignKey(
        "ForwardManyToOne",
        on_delete=CASCADE,
        related_name="example_rels",
    )
    forward_many_to_many_fields = ManyToManyField(
        "ForwardManyToMany",
        related_name="example_rels",
    )

    named_relation = ForeignKey(
        "app.Task",
        on_delete=CASCADE,
        related_name="+",
    )


# --------------------------------------------------------------------


class ForwardOneToOne(BaseModel):
    forward_one_to_one_field = OneToOneField(
        "ForwardOneToOneForRelated",
        on_delete=CASCADE,
        related_name="forward_one_to_one_rel",
    )
    forward_many_to_one_field = ForeignKey(
        "ForwardManyToOneForRelated",
        on_delete=CASCADE,
        related_name="forward_one_to_one_rels",
    )
    forward_many_to_many_fields = ManyToManyField(
        "ForwardManyToManyForRelated",
        related_name="forward_one_to_one_rels",
    )


class ForwardManyToOne(BaseModel):
    forward_one_to_one_field = OneToOneField(
        "ForwardOneToOneForRelated",
        on_delete=CASCADE,
        related_name="forward_many_to_one_rel",
    )
    forward_many_to_one_field = ForeignKey(
        "ForwardManyToOneForRelated",
        on_delete=CASCADE,
        related_name="forward_many_to_one_rels",
    )
    forward_many_to_many_fields = ManyToManyField(
        "ForwardManyToManyForRelated",
        related_name="forward_many_to_one_rels",
    )


class ForwardManyToMany(BaseModel):
    forward_one_to_one_field = OneToOneField(
        "ForwardOneToOneForRelated",
        on_delete=CASCADE,
        related_name="forward_many_to_many_rel",
    )
    forward_many_to_one_field = ForeignKey(
        "ForwardManyToOneForRelated",
        on_delete=CASCADE,
        related_name="forward_many_to_many_rels",
    )
    forward_many_to_many_fields = ManyToManyField(
        "ForwardManyToManyForRelated",
        related_name="forward_many_to_many_rels",
    )


class ReverseOneToOne(BaseModel):
    example_field = OneToOneField(
        "Example",
        on_delete=CASCADE,
        related_name="reverse_one_to_one_rel",
    )

    forward_one_to_one_field = OneToOneField(
        "ForwardOneToOneForRelated",
        on_delete=CASCADE,
        related_name="reverse_one_to_one_rel",
    )
    forward_many_to_one_field = ForeignKey(
        "ForwardManyToOneForRelated",
        on_delete=CASCADE,
        related_name="reverse_one_to_one_rels",
    )
    forward_many_to_many_fields = ManyToManyField(
        "ForwardManyToManyForRelated",
        related_name="reverse_one_to_one_rels",
    )


class ReverseOneToMany(BaseModel):
    example_field = ForeignKey(
        "Example",
        on_delete=CASCADE,
        related_name="reverse_one_to_many_rels",
    )

    forward_one_to_one_field = OneToOneField(
        "ForwardOneToOneForRelated",
        on_delete=CASCADE,
        related_name="reverse_one_to_many_rel",
    )
    forward_many_to_one_field = ForeignKey(
        "ForwardManyToOneForRelated",
        on_delete=CASCADE,
        related_name="reverse_one_to_many_rels",
    )
    forward_many_to_many_fields = ManyToManyField(
        "ForwardManyToManyForRelated",
        related_name="reverse_one_to_many_rels",
    )


class ReverseManyToMany(BaseModel):
    example_fields = ManyToManyField(
        "Example",
        related_name="reverse_many_to_many_rels",
    )

    forward_one_to_one_field = OneToOneField(
        "ForwardOneToOneForRelated",
        on_delete=CASCADE,
        related_name="reverse_many_to_many_rel",
    )
    forward_many_to_one_field = ForeignKey(
        "ForwardManyToOneForRelated",
        on_delete=CASCADE,
        related_name="reverse_many_to_many_rels",
    )
    forward_many_to_many_fields = ManyToManyField(
        "ForwardManyToManyForRelated",
        related_name="reverse_many_to_many_rels",
    )


# --------------------------------------------------------------------


class ForwardOneToOneForRelated(BaseModel):
    pass


class ForwardManyToOneForRelated(BaseModel):
    pass


class ForwardManyToManyForRelated(BaseModel):
    pass


# --------------------------------------------------------------------


class ReverseOneToOneToForwardOneToOne(BaseModel):
    forward_one_to_one_field = OneToOneField(
        "ForwardOneToOne",
        on_delete=CASCADE,
        related_name="reverse_one_to_one_rel",
    )


class ReverseOneToOneToForwardManyToOne(BaseModel):
    forward_many_to_one_field = OneToOneField(
        "ForwardManyToOne",
        on_delete=CASCADE,
        related_name="reverse_one_to_one_rel",
    )


class ReverseOneToOneToForwardManyToMany(BaseModel):
    forward_many_to_many_field = OneToOneField(
        "ForwardManyToMany",
        on_delete=CASCADE,
        related_name="reverse_one_to_one_rel",
    )


class ReverseOneToOneToReverseOneToOne(BaseModel):
    reverse_one_to_one_field = OneToOneField(
        "ReverseOneToOne",
        on_delete=CASCADE,
        related_name="reverse_one_to_one_rel",
    )


class ReverseOneToOneToReverseOneToMany(BaseModel):
    reverse_many_to_one_field = OneToOneField(
        "ReverseOneToMany",
        on_delete=CASCADE,
        related_name="reverse_one_to_one_rel",
    )


class ReverseOneToOneToReverseManyToMany(BaseModel):
    reverse_many_to_many_field = OneToOneField(
        "ReverseManyToMany",
        on_delete=CASCADE,
        related_name="reverse_one_to_one_rel",
    )


# --------------------------------------------------------------------


class ReverseOneToManyToForwardOneToOne(BaseModel):
    forward_one_to_one_field = ForeignKey(
        "ForwardOneToOne",
        on_delete=CASCADE,
        related_name="reverse_one_to_many_rels",
    )


class ReverseOneToManyToForwardManyToOne(BaseModel):
    forward_many_to_one_field = ForeignKey(
        "ForwardManyToOne",
        on_delete=CASCADE,
        related_name="reverse_one_to_many_rels",
    )


class ReverseOneToManyToForwardManyToMany(BaseModel):
    forward_many_to_many_field = ForeignKey(
        "ForwardManyToMany",
        on_delete=CASCADE,
        related_name="reverse_one_to_many_rels",
    )


class ReverseOneToManyToReverseOneToOne(BaseModel):
    reverse_one_to_one_field = ForeignKey(
        "ReverseOneToOne",
        on_delete=CASCADE,
        related_name="reverse_one_to_many_rels",
    )


class ReverseOneToManyToReverseOneToMany(BaseModel):
    reverse_many_to_one_field = ForeignKey(
        "ReverseOneToMany",
        on_delete=CASCADE,
        related_name="reverse_one_to_many_rels",
    )


class ReverseOneToManyToReverseManyToMany(BaseModel):
    reverse_many_to_many_field = ForeignKey(
        "ReverseManyToMany",
        on_delete=CASCADE,
        related_name="reverse_one_to_many_rels",
    )


# --------------------------------------------------------------------


class ReverseManyToManyToForwardOneToOne(BaseModel):
    forward_one_to_one_fields = ManyToManyField(
        "ForwardOneToOne",
        related_name="reverse_many_to_many_rels",
    )


class ReverseManyToManyToForwardManyToOne(BaseModel):
    forward_many_to_one_fields = ManyToManyField(
        "ForwardManyToOne",
        related_name="reverse_many_to_many_rels",
    )


class ReverseManyToManyToForwardManyToMany(BaseModel):
    forward_many_to_many_fields = ManyToManyField(
        "ForwardManyToMany",
        related_name="reverse_many_to_many_rels",
    )


class ReverseManyToManyToReverseOneToOne(BaseModel):
    reverse_one_to_one_fields = ManyToManyField(
        "ReverseOneToOne",
        related_name="reverse_many_to_many_rels",
    )


class ReverseManyToManyToReverseOneToMany(BaseModel):
    reverse_many_to_one_fields = ManyToManyField(
        "ReverseOneToMany",
        related_name="reverse_many_to_many_rels",
    )


class ReverseManyToManyToReverseManyToMany(BaseModel):
    reverse_many_to_many_fields = ManyToManyField(
        "ReverseManyToMany",
        related_name="reverse_many_to_many_rels",
    )
