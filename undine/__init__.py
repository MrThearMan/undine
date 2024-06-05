from __future__ import annotations

from django.conf import settings

# Configure Django settings if not configured.
# This is required for `__main__.py` to work when calling `python -m undine`.
if not settings.configured:  # pragma: no cover
    settings.configure()

from .calculation import Calculation, CalculationArgument
from .entrypoint import Entrypoint, RootType
from .filtering import Filter, FilterSet
from .http.views import GraphQLView
from .interface import InterfaceField, InterfaceType
from .mutation import Input, MutationType
from .ordering import Order, OrderSet
from .query import Field, QueryType
from .schema import create_schema
from .typing import DjangoExpression, GQLInfo
from .union import UnionType

__all__ = [
    "Calculation",
    "CalculationArgument",
    "DjangoExpression",
    "Entrypoint",
    "Field",
    "Filter",
    "FilterSet",
    "GQLInfo",
    "GraphQLView",
    "Input",
    "InterfaceField",
    "InterfaceType",
    "MutationType",
    "Order",
    "OrderSet",
    "QueryType",
    "RootType",
    "UnionType",
    "create_schema",
]
