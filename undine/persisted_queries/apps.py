from django.apps import AppConfig


class UndinePersistedQueriesConfig(AppConfig):
    name = "undine.persisted_queries"
    label = "persisted_queries"
    verbose_name = "persisted queries"
    default_auto_field = "django.db.models.BigAutoField"
