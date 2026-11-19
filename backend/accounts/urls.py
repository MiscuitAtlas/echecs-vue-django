from django.urls import path

from . import views

urlpatterns = [
    path("session", views.session),
    path("inscription", views.register),
    path("connexion", views.login_view),
    path("invite", views.guest),
    path("deconnexion", views.logout_view),
    path("compte/mot-de-passe", views.change_password),
    path("compte/suppression", views.delete_account),
]
