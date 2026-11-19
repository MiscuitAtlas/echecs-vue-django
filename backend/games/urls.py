from django.urls import path

from . import views

urlpatterns = [
    path("parties", views.games),
    path("parties/<str:code>", views.game),
    path("parties/<str:code>/rejoindre", views.join),
    path("parties/<str:code>/coups", views.move),
    path("parties/<str:code>/abandon", views.resign),
    path("parties/<str:code>/nulle", views.draw),
    path("parties/<str:code>/messages", views.messages),
]
