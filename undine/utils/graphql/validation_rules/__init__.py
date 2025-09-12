from __future__ import annotations

import itertools
from typing import TYPE_CHECKING

from graphql import NoSchemaIntrospectionCustomRule, specified_rules

from undine.settings import undine_settings

from .max_alias_count import MaxAliasCountRule
from .max_complexity_rule import MaxComplexityRule
from .max_directive_count import MaxDirectiveCountRule
from .one_of_input_object import OneOfInputObjectTypeRule, core_implements_one_of_directive
from .visibility_rule import get_visibility_rule

if TYPE_CHECKING:
    from graphql import ASTValidationRule

    from undine.typing import DjangoRequestProtocol


__all__ = [
    "get_validation_rules",
]


def get_validation_rules(request: DjangoRequestProtocol | None = None) -> tuple[type[ASTValidationRule], ...]:
    """Get the GraphQL validation rules based on project current settings."""
    visibility_enabled = undine_settings.EXPERIMENTAL_VISIBILITY_CHECKS and request is not None
    return tuple(
        itertools.chain(
            specified_rules,
            [MaxAliasCountRule, MaxDirectiveCountRule, MaxComplexityRule],
            [] if not visibility_enabled else [get_visibility_rule(request=request)],
            [] if core_implements_one_of_directive() else [OneOfInputObjectTypeRule],
            [] if undine_settings.ALLOW_INTROSPECTION_QUERIES else [NoSchemaIntrospectionCustomRule],
            undine_settings.ADDITIONAL_VALIDATION_RULES,
        )
    )
