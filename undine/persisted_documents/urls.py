from __future__ import annotations

from django.urls import path

from undine.settings import undine_settings

from .views import persisted_documents_view

app_name = "undine.persisted_documents"

urlpatterns = [
    path(
        undine_settings.PERSISTED_DOCUMENTS_PATH,
        persisted_documents_view,
        name=undine_settings.PERSISTED_DOCUMENTS_VIEW_NAME,
    ),
]
