from django.urls import include, path

urlpatterns = [
    path("", include("undine.http.urls")),
]
