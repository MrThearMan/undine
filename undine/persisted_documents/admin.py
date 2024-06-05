from __future__ import annotations

from typing import TYPE_CHECKING

from django.contrib import admin

from .models import PersistedDocument

if TYPE_CHECKING:
    from django.http import HttpRequest


__all__ = [
    "PersistedDocumentAdmin",
]


@admin.register(PersistedDocument)
class PersistedDocumentAdmin(admin.ModelAdmin):
    list_display = ("document_id", "created_at")
    search_fields = ("document_id", "document")
    fields = ("document_id", "document", "created_at")
    readonly_fields = ("document_id", "document", "created_at")

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_change_permission(self, request: HttpRequest, obj: PersistedDocument | None = None) -> bool:
        return False

    def has_delete_permission(self, request: HttpRequest, obj: PersistedDocument | None = None) -> bool:
        return False
