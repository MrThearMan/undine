from __future__ import annotations

from typing import TYPE_CHECKING, Any

from django.core.exceptions import ValidationError
from django.db.models import CharField

from undine.utils.text import comma_sep_str

if TYPE_CHECKING:
    from collections.abc import Sequence

    from django.db.models import TextChoices


__all__ = [
    "TextChoicesField",
]


class TextChoicesField(CharField):
    """Choice field that offers more consistent naming for enums in the GraphQL Schema."""

    default_error_messages = {
        "invalid": "`%(value)s` is not a member of the `%(enum_name)s` enum. Choices are: %(choices)s.",
    }

    def __init__(self, choices_enum: type[TextChoices], **kwargs: Any) -> None:
        """
        A field for enums that use TextChoices.
        Automatically adds 'max_length' validator based on the enum values.
        Values fetched from the database are converted to the enum type.

        :param choices_enum: `TextChoices` class to use for the field.
        :param kwargs: Keyword arguments to pass to the `CharField` constructor.
        """
        self.choices_enum = choices_enum
        kwargs["choices"] = choices_enum.choices
        kwargs["max_length"] = max(len(val) for val in choices_enum.values)
        super().__init__(**kwargs)

    def deconstruct(self) -> tuple[str, str, Sequence[str], dict[str, Any]]:
        """Returns a tuple with enough information to recreate the field."""
        name, path, args, kwargs = super().deconstruct()
        kwargs["choices_enum"] = self.choices_enum
        return name, path, args, kwargs

    def to_python(self, value: Any) -> Any:
        """Converts the given value into the correct Python object for this field."""
        # The database can return `None` even if this field is not nullable
        # in case the field selected through a relation where the relationship itself is null.
        #
        # When saving to database, we can return `None` here since the database
        # will throw an `IntegrityError` if the field is not nullable.
        if value is None:
            return None

        try:
            return self.choices_enum(value)
        except ValueError as error:
            params = {
                "value": value,
                "enum_name": self.choices_enum.__name__,
                "choices": comma_sep_str(self.choices_enum.values, last_sep="and", quote=True),
            }
            error_dict = {self.attname: self.error_messages["invalid"] % params}
            raise ValidationError(error_dict, code="invalid") from error

    def from_db_value(self, value: Any, expression: Any, connection: Any) -> Any:
        """Converts a value as returned by the database to a Python object."""
        return self.to_python(value)

    def get_prep_value(self, value: Any) -> Any:
        """Converts the given value into a value suitable for the database."""
        return self.to_python(value)
