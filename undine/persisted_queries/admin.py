from django.contrib import admin

from .models import PersistedQuery


@admin.register(PersistedQuery)
class PersistedQueryAdmin(admin.ModelAdmin):
    list_display = ("name", "created_at", "modified_at")
    search_fields = ("name", "document")
