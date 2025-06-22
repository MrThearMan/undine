from __future__ import annotations

from django.urls import path

from undine.settings import undine_settings

from .views import GraphQLView

app_name = "undine"

urlpatterns = [
    path(undine_settings.GRAPHQL_PATH, GraphQLView.as_view(), name=undine_settings.GRAPHQL_VIEW_NAME),
]
