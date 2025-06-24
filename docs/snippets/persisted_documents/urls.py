from django.urls import include, path

urlpatterns = [
    path("", include("undine.http.urls")),
    path("", include("undine.persisted_documents.urls")),
]
