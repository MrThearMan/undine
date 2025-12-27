from __future__ import annotations

import itertools
from typing import TYPE_CHECKING

from graphql import NoSchemaIntrospectionCustomRule, specified_rules

from undine.settings import undine_settings
from undine.typing import DjangoRequestProtocol

from .max_alias_count import MaxAliasCountRule
from .max_complexity_rule import MaxComplexityRule
from .max_directive_count import MaxDirectiveCountRule
from .one_of_input_object import OneOfInputObjectTypeRule, core_implements_one_of_directive
from .visibility_rule import VisibilityRule

if TYPE_CHECKING:
    from graphql import ASTValidationRule


__all__ = [
    "DjangoRequestProtocol",
    "get_validation_rules",
]


def get_validation_rules(*, inside_request: bool = False) -> tuple[type[ASTValidationRule], ...]:
    """Get the GraphQL validation rules based on project current settings."""
    visibility_enabled = inside_request and undine_settings.EXPERIMENTAL_VISIBILITY_CHECKS
    return tuple(
        itertools.chain(
            specified_rules,
            [MaxAliasCountRule, MaxDirectiveCountRule, MaxComplexityRule],
            [] if not visibility_enabled else [VisibilityRule],
            [] if core_implements_one_of_directive() else [OneOfInputObjectTypeRule],
            [] if undine_settings.ALLOW_INTROSPECTION_QUERIES else [NoSchemaIntrospectionCustomRule],
            undine_settings.ADDITIONAL_VALIDATION_RULES,
        )
    )
