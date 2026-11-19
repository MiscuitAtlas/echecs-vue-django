from django.urls import include, path, re_path

from . import views

urlpatterns = [
    path("api/", include("accounts.urls")),
    path("api/", include("games.urls")),
    re_path(r"^api/(?P<path>.*)$", views.api_not_found),
    re_path(r"^(?P<path>(?!ws/).*)$", views.frontend),
]
