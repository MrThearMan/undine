from __future__ import annotations

from typing import Any

from graphql import DirectiveLocation, GraphQLID, GraphQLNonNull

from undine import Entrypoint, Field, GQLInfo, QueryType, RootType
from undine.directives import Directive
from undine.federation import (
    ComposeDirectiveDirective,
    ExternalDirective,
    FederationField,
    FederationType,
    InaccessibleDirective,
    InterfaceObjectDirective,
    KeyDirective,
    LinkDirective,
    OverrideDirective,
    ProvidesDirective,
    RequiresDirective,
    ShareableDirective,
    TagDirective,
    create_federation_schema,
)
from undine.optimizer import optimize_sync
from undine.typing import ID

from .models import (
    CaseStudy,
    DeprecatedProduct,
    Inventory,
    Product,
    ProductDimension,
    ProductResearch,
    ProductVariation,
    User,
)

__all__ = [
    "schema",
]


class CustomDirective(Directive, locations=[DirectiveLocation.OBJECT], schema_name="custom"): ...


class ProductVariationType(QueryType[ProductVariation], schema_name="ProductVariation"):
    id = Field(GraphQLNonNull(GraphQLID))


class CaseStudyType(QueryType[CaseStudy], schema_name="CaseStudy"):
    case_number = Field(GraphQLNonNull(GraphQLID))
    description = Field()


@KeyDirective(fields="study { caseNumber }")
class ProductResearchType(QueryType[ProductResearch], schema_name="ProductResearch"):
    study = Field(CaseStudyType, complexity=0)
    outcome = Field()

    @classmethod
    def __resolve_reference__(cls, representation: dict[str, Any], info: GQLInfo) -> ProductResearch | None:
        case_number = (representation.get("study") or {}).get("caseNumber")
        if case_number is None:
            return None
        return ProductResearch.objects.filter(study_id=case_number).first()


@ShareableDirective()
class ProductDimensionType(QueryType[ProductDimension], schema_name="ProductDimension"):
    size = Field()
    weight = Field()
    unit = Field() @ InaccessibleDirective()


@KeyDirective(fields="email")
class UserExtension(FederationType, schema_name="User"):
    average_products_created_per_year = FederationField(int, nullable=True) @ RequiresDirective(
        fields="totalProductsCreated yearsOfEmployment",
    )
    email = FederationField(GraphQLNonNull(GraphQLID)) @ ExternalDirective()
    name = FederationField(str, nullable=True) @ OverrideDirective(from_="users")
    total_products_created = FederationField(int, nullable=True) @ ExternalDirective()
    years_of_employment = FederationField(int) @ ExternalDirective()

    @name.resolve
    def _resolve_name(self, info: GQLInfo) -> str | None:
        return self.name

    @average_products_created_per_year.resolve
    def _resolve_average(self, info: GQLInfo) -> int | None:
        if self.total_products_created is None:
            return None
        return round(self.total_products_created / self.years_of_employment)

    @classmethod
    def __resolve_reference__(cls, representation: dict[str, Any], info: GQLInfo) -> UserExtension | None:
        email = representation.get("email")
        if email is None:
            return None

        user = User.objects.get(email=email)
        if user is None:
            return None

        return cls(
            email=email,
            name=user.name,
            total_products_created=representation.get("totalProductsCreated", user.total_products_created),
            years_of_employment=representation.get("yearsOfEmployment", user.years_of_employment),
        )


@KeyDirective(fields="sku package")
class DeprecatedProductType(QueryType[DeprecatedProduct], schema_name="DeprecatedProduct"):
    sku = Field()
    package = Field()
    reason = Field()
    created_by = Field(UserExtension, nullable=True)

    @created_by.resolve
    def _resolve_created_by(root: DeprecatedProduct, info: GQLInfo) -> UserExtension | None:
        user: User | None = User.objects.first()
        if user is None:
            return None

        return UserExtension(
            email=user.email,
            name=user.name,
            total_products_created=user.total_products_created,
            years_of_employment=user.years_of_employment,
        )

    @classmethod
    def __resolve_reference__(cls, representation: dict[str, Any], info: GQLInfo) -> DeprecatedProduct | None:
        sku = representation.get("sku")
        package = representation.get("package")
        if sku is None or package is None:
            return None
        return DeprecatedProduct.objects.filter(sku=sku, package=package).first()


@CustomDirective()
@KeyDirective(fields="id")
@KeyDirective(fields="sku package")
@KeyDirective(fields="sku variation { id }")
class ProductType(QueryType[Product], schema_name="Product"):
    id = Field(GraphQLNonNull(GraphQLID))
    sku = Field()
    package = Field()
    variation = Field(ProductVariationType, nullable=True, complexity=0)
    dimensions = Field(ProductDimensionType, nullable=True, complexity=0)
    created_by = Field(UserExtension, nullable=True) @ ProvidesDirective(fields="totalProductsCreated")
    notes = Field() @ TagDirective(name="internal")
    research = Field(ProductResearchType, many=True, complexity=0)

    @created_by.resolve
    def _resolve_created_by(root: Product, info: GQLInfo) -> UserExtension | None:
        user: User | None = User.objects.first()
        if user is None:
            return None

        return UserExtension(
            email=user.email,
            name=user.name,
            total_products_created=user.total_products_created,
            years_of_employment=user.years_of_employment,
        )

    @classmethod
    def __resolve_reference__(cls, representation: dict[str, Any], info: GQLInfo) -> Product | None:
        if "id" in representation:
            return Product.objects.filter(pk=representation["id"]).first()

        sku = representation.get("sku")
        if sku is None:
            return None

        if "package" in representation:
            return Product.objects.filter(sku=sku, package=representation["package"]).first()

        variation = representation.get("variation") or {}
        variation_id = variation.get("id")
        if variation_id is not None:
            return Product.objects.filter(sku=sku, variation_id=variation_id).first()

        return None


class Query(RootType):
    product = Entrypoint(ProductType, nullable=True, complexity=0)

    deprecated_product = Entrypoint(
        DeprecatedProductType,
        nullable=True,
        deprecation_reason="Use product query instead",
        complexity=0,
    )

    @product.resolve
    def _resolve_product(root: Any, info: GQLInfo, id: ID) -> Product | None:  # noqa: A002
        return optimize_sync(Product.objects.all(), info, pk=id)

    @deprecated_product.resolve
    def _resolve_deprecated_product(root: Any, info: GQLInfo, sku: str, package: str) -> DeprecatedProduct | None:
        return optimize_sync(DeprecatedProduct.objects.all(), info, sku=sku, package=package)


@InterfaceObjectDirective()
@KeyDirective(fields="id")
class InventoryType(QueryType[Inventory], schema_name="Inventory"):
    id = Field(GraphQLNonNull(GraphQLID))
    deprecated_products = Field(DeprecatedProductType, many=True, complexity=0)


schema = create_federation_schema(
    query=Query,
    schema_definition_directives=[
        LinkDirective(url="https://myspecs.dev/myCustomDirective/v1.0", import_=["@custom"]),
        ComposeDirectiveDirective(name="@custom"),
    ],
)
