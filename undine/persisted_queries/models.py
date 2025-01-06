from django.db.models import CharField, DateTimeField, Model, TextField

from .validators import validate_document, validate_name

__all__ = [
    "PersistedQuery",
]


class PersistedQuery(Model):
    """A persisted query."""

    name = CharField(max_length=255, primary_key=True, validators=[validate_name])
    document = TextField(validators=[validate_document])
    created_at = DateTimeField(auto_now_add=True)
    modified_at = DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "persisted query"
        verbose_name_plural = "persisted queries"

    def __str__(self) -> str:
        return f"Persisted query '{self.name}'"
