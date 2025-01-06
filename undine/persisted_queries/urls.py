from django.urls import re_path

from .views import execute_persisted_query

app_name = "persisted_queries"

urlpatterns = [
    re_path("persisted-query/(?P<name>[a-zA-Z]{1,255})", execute_persisted_query, name="persisted_query"),
]
