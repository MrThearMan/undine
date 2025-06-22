from __future__ import annotations

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from undine.persisted_documents.views import PersistedDocumentsView

urlpatterns = [
    path("", include("undine.http.urls")),
    path("persisted-documents/", PersistedDocumentsView.as_view(), name="persisted_documents"),
    path("admin/", admin.site.urls),
    path("__debug__/", include("debug_toolbar.urls")),
]


if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
