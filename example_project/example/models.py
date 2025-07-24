from __future__ import annotations

from typing import TYPE_CHECKING

from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.db.models import (
    CASCADE,
    CharField,
    ForeignKey,
    Index,
    ManyToManyField,
    Model,
    OneToOneField,
    PositiveIntegerField,
)

if TYPE_CHECKING:
    from example_project.project.typing import RelatedManager

__all__ = [
    "Example",
    "ExampleFFK",
    "ExampleFMTM",
    "ExampleFOTO",
    "ExampleGeneric",
    "ExampleRFK",
    "ExampleRMTM",
    "ExampleROTO",
    "NestedExampleFFK",
    "NestedExampleFMTM",
    "NestedExampleFOTO",
    "NestedExampleRFK",
    "NestedExampleRMTM",
    "NestedExampleROTO",
]


class BaseModel(Model):
    name = CharField(max_length=255)

    class Meta:
        ordering = ["pk"]
        abstract = True

    def __str__(self) -> str:
        return self.__class__.__name__ + ": " + self.name


# --------------------------------------------------------------------


class ExampleGeneric(BaseModel):
    content_type = ForeignKey(ContentType, on_delete=CASCADE)
    object_id = PositiveIntegerField()
    content_object = GenericForeignKey("content_type", "object_id")

    class Meta:
        indexes = [
            Index(fields=["content_type", "object_id"]),
        ]


# --------------------------------------------------------------------


class Example(BaseModel):
    symmetrical_field = ManyToManyField("self", symmetrical=True)

    generic = GenericRelation(ExampleGeneric)

    example_foto = OneToOneField("ExampleFOTO", related_name="example", on_delete=CASCADE, null=True, blank=True)
    example_ffk = ForeignKey("ExampleFFK", related_name="example_set", on_delete=CASCADE, null=True, blank=True)
    example_fmtm_set = ManyToManyField("ExampleFMTM", related_name="example_set")

    example_roto: ExampleROTO | None
    example_rfk_set: RelatedManager[ExampleRFK]
    example_rmtm_set: RelatedManager[ExampleRMTM]


# --------------------------------------------------------------------


class ExampleFOTO(BaseModel):
    example: Example | None

    example_foto = OneToOneField(
        "NestedExampleFOTO",
        on_delete=CASCADE,
        related_name="example_foto",
        null=True,
        blank=True,
    )
    example_ffk = ForeignKey(
        "NestedExampleFFK",
        on_delete=CASCADE,
        related_name="example_foto_set",
        null=True,
        blank=True,
    )
    example_fmtm_set = ManyToManyField("NestedExampleFMTM", related_name="example_foto_set")

    example_roto: NestedExampleROTO | None
    example_rfk_set: RelatedManager[NestedExampleRFK]
    example_rmtm_set: RelatedManager[NestedExampleRMTM]


class ExampleFFK(BaseModel):
    example_set: RelatedManager[Example]

    example_foto = OneToOneField(
        "NestedExampleFOTO",
        on_delete=CASCADE,
        related_name="example_ffk",
        null=True,
        blank=True,
    )
    example_ffk = ForeignKey(
        "NestedExampleFFK",
        on_delete=CASCADE,
        related_name="example_ffk_set",
        null=True,
        blank=True,
    )
    example_fmtm_set = ManyToManyField("NestedExampleFMTM", related_name="example_ffk_set")

    example_roto: NestedExampleROTO | None
    example_rfk_set: RelatedManager[NestedExampleRFK]
    example_rmtm_set: RelatedManager[NestedExampleRMTM]


class ExampleFMTM(BaseModel):
    example_set: RelatedManager[Example]

    example_foto = OneToOneField(
        "NestedExampleFOTO",
        on_delete=CASCADE,
        related_name="example_fmtm",
        null=True,
        blank=True,
    )
    example_ffk = ForeignKey(
        "NestedExampleFFK",
        on_delete=CASCADE,
        related_name="example_fmtm_set",
        null=True,
        blank=True,
    )
    example_fmtm_set = ManyToManyField("NestedExampleFMTM", related_name="example_fmtm_set")

    example_roto: NestedExampleROTO | None
    example_rfk_set: RelatedManager[NestedExampleRFK]
    example_rmtm_set: RelatedManager[NestedExampleRMTM]


# --------------------------------------------------------------------


class ExampleROTO(BaseModel):
    example = OneToOneField("Example", on_delete=CASCADE, related_name="example_roto", null=True, blank=True)

    example_foto = OneToOneField(
        "NestedExampleFOTO",
        on_delete=CASCADE,
        related_name="example_roto",
        null=True,
        blank=True,
    )
    example_ffk = ForeignKey(
        "NestedExampleFFK",
        on_delete=CASCADE,
        related_name="example_roto_set",
        null=True,
        blank=True,
    )
    example_fmtm_set = ManyToManyField("NestedExampleFMTM", related_name="example_roto_set")

    example_roto: NestedExampleROTO | None
    example_rfk_set: RelatedManager[NestedExampleRFK]
    example_rmtm_set: RelatedManager[NestedExampleRMTM]


class ExampleRFK(BaseModel):
    example = ForeignKey("Example", on_delete=CASCADE, related_name="example_rfk_set", null=True, blank=True)

    example_foto = OneToOneField(
        "NestedExampleFOTO",
        on_delete=CASCADE,
        related_name="example_rfk",
        null=True,
        blank=True,
    )
    example_ffk = ForeignKey(
        "NestedExampleFFK",
        on_delete=CASCADE,
        related_name="example_rfk_set",
        null=True,
        blank=True,
    )
    example_fmtm_set = ManyToManyField("NestedExampleFMTM", related_name="example_rfk_set")

    example_roto: NestedExampleROTO | None
    example_rfk_set: RelatedManager[NestedExampleRFK]
    example_rmtm_set: RelatedManager[NestedExampleRMTM]


class ExampleRMTM(BaseModel):
    examples = ManyToManyField("Example", related_name="example_rmtm_set")

    example_foto = OneToOneField(
        "NestedExampleFOTO",
        on_delete=CASCADE,
        related_name="example_rmtm",
        null=True,
        blank=True,
    )
    example_ffk = ForeignKey(
        "NestedExampleFFK",
        on_delete=CASCADE,
        related_name="example_rmtm_set",
        null=True,
        blank=True,
    )
    example_fmtm_set = ManyToManyField("NestedExampleFMTM", related_name="example_rmtm_set")

    example_roto: NestedExampleROTO | None
    example_rfk_set: RelatedManager[NestedExampleRFK]
    example_rmtm_set: RelatedManager[NestedExampleRMTM]


# --------------------------------------------------------------------


class NestedExampleFOTO(BaseModel):
    example_foto: ExampleFOTO | None
    example_ffk: ExampleFFK | None
    example_fmtm: ExampleFMTM | None

    example_roto: ExampleROTO | None
    example_rfk: ExampleRFK | None
    example_rmtm: ExampleRMTM | None


class NestedExampleFFK(BaseModel):
    example_foto_set: RelatedManager[ExampleFOTO]
    example_ffk_set: RelatedManager[ExampleFFK]
    example_fmtm_set: RelatedManager[ExampleFMTM]

    example_roto_set: RelatedManager[ExampleROTO]
    example_rfk_set: RelatedManager[ExampleRFK]
    example_rmtm_set: RelatedManager[ExampleRMTM]


class NestedExampleFMTM(BaseModel):
    example_foto_set: RelatedManager[ExampleFOTO]
    example_ffk_set: RelatedManager[ExampleFFK]
    example_fmtm_set: RelatedManager[ExampleFMTM]

    example_roto_set: RelatedManager[ExampleROTO]
    example_rfk_set: RelatedManager[ExampleRFK]
    example_rmtm_set: RelatedManager[ExampleRMTM]


# --------------------------------------------------------------------


class NestedExampleROTO(BaseModel):
    example_foto = OneToOneField("ExampleFOTO", on_delete=CASCADE, related_name="example_roto", null=True, blank=True)
    example_ffk = OneToOneField("ExampleFFK", on_delete=CASCADE, related_name="example_roto", null=True, blank=True)
    example_fmtm = OneToOneField("ExampleFMTM", on_delete=CASCADE, related_name="example_roto", null=True, blank=True)

    example_roto = OneToOneField("ExampleROTO", on_delete=CASCADE, related_name="example_roto", null=True, blank=True)
    example_rfk = OneToOneField("ExampleRFK", on_delete=CASCADE, related_name="example_roto", null=True, blank=True)
    example_rmtm = OneToOneField("ExampleRMTM", on_delete=CASCADE, related_name="example_roto", null=True, blank=True)


class NestedExampleRFK(BaseModel):
    example_foto = ForeignKey("ExampleFOTO", on_delete=CASCADE, related_name="example_rfk_set", null=True, blank=True)
    example_ffk = ForeignKey("ExampleFFK", on_delete=CASCADE, related_name="example_rfk_set", null=True, blank=True)
    example_fmtm = ForeignKey("ExampleFMTM", on_delete=CASCADE, related_name="example_rfk_set", null=True, blank=True)

    example_roto = ForeignKey("ExampleROTO", on_delete=CASCADE, related_name="example_rfk_set", null=True, blank=True)
    example_rfk = ForeignKey("ExampleRFK", on_delete=CASCADE, related_name="example_rfk_set", null=True, blank=True)
    example_rmtm = ForeignKey("ExampleRMTM", on_delete=CASCADE, related_name="example_rfk_set", null=True, blank=True)


class NestedExampleRMTM(BaseModel):
    example_foto_set = ManyToManyField("ExampleFOTO", related_name="example_rmtm_set")
    example_ffk_set = ManyToManyField("ExampleFFK", related_name="example_rmtm_set")
    example_fmtm_set = ManyToManyField("ExampleFMTM", related_name="example_rmtm_set")

    example_roto_set = ManyToManyField("ExampleROTO", related_name="example_rmtm_set")
    example_rfk_set = ManyToManyField("ExampleRFK", related_name="example_rmtm_set")
    example_rmtm_set = ManyToManyField("ExampleRMTM", related_name="example_rmtm_set")


# --------------------------------------------------------------------
