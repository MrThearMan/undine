from __future__ import annotations

from typing import ClassVar

from django.contrib.auth.models import AbstractUser
from django.db.models import (
    CASCADE,
    SET_NULL,
    CharField,
    FloatField,
    ForeignKey,
    IntegerField,
    Manager,
    ManyToManyField,
    Model,
    UniqueConstraint,
)


class User(AbstractUser):
    name = CharField(max_length=255, null=True, blank=True)  # noqa: DJ001
    total_products_created = IntegerField(null=True, blank=True)
    years_of_employment = IntegerField(null=True, blank=True)

    objects: ClassVar[Manager]

    class Meta:
        db_table = "users"
        app_label = "products"


class ProductVariation(Model):
    id = CharField(primary_key=True, max_length=255)

    objects: ClassVar[Manager]

    class Meta:
        db_table = "product_variations"
        app_label = "products"


class ProductDimension(Model):
    size = CharField(max_length=255, null=True, blank=True)  # noqa: DJ001
    weight = FloatField(null=True, blank=True)
    unit = CharField(max_length=32, null=True, blank=True)  # noqa: DJ001

    objects: ClassVar[Manager]

    class Meta:
        db_table = "product_dimensions"
        app_label = "products"


class CaseStudy(Model):
    case_number = CharField(primary_key=True, max_length=255)
    description = CharField(max_length=255, null=True, blank=True)  # noqa: DJ001

    objects: ClassVar[Manager]

    class Meta:
        db_table = "case_studies"
        app_label = "products"


class ProductResearch(Model):
    study = ForeignKey(CaseStudy, on_delete=CASCADE, related_name="research")
    outcome = CharField(max_length=255, null=True, blank=True)  # noqa: DJ001

    objects: ClassVar[Manager]

    class Meta:
        db_table = "product_research"
        app_label = "products"


class Product(Model):
    id = CharField(primary_key=True, max_length=255)
    sku = CharField(max_length=255, null=True, blank=True)  # noqa: DJ001
    package = CharField(max_length=255, null=True, blank=True)  # noqa: DJ001
    variation = ForeignKey(
        ProductVariation,
        on_delete=SET_NULL,
        null=True,
        blank=True,
        related_name="products",
    )
    dimensions = ForeignKey(
        ProductDimension,
        on_delete=SET_NULL,
        null=True,
        blank=True,
        related_name="products",
    )
    research = ManyToManyField(ProductResearch, related_name="products")
    notes = CharField(max_length=255, null=True, blank=True)  # noqa: DJ001

    objects: ClassVar[Manager]

    class Meta:
        db_table = "products"
        app_label = "products"


class DeprecatedProduct(Model):
    sku = CharField(max_length=255)
    package = CharField(max_length=255)
    reason = CharField(max_length=255, null=True, blank=True)  # noqa: DJ001

    objects: ClassVar[Manager]

    class Meta:
        db_table = "deprecated_products"
        app_label = "products"
        constraints = [
            UniqueConstraint(fields=["sku", "package"], name="deprecated_product_sku_package"),
        ]


class Inventory(Model):
    id = CharField(primary_key=True, max_length=255)
    deprecated_products = ManyToManyField(DeprecatedProduct, related_name="inventories")

    objects: ClassVar[Manager]

    class Meta:
        db_table = "inventories"
        app_label = "products"
