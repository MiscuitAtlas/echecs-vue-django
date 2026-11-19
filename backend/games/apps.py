from django.apps import AppConfig
from django.db.models.signals import pre_delete


class GamesConfig(AppConfig):
    name = "games"
    verbose_name = "Parties"

    def ready(self):
        from django.contrib.auth import get_user_model

        from .services import forfeit_all

        def before_user_deleted(sender, instance, **kwargs):
            forfeit_all(instance)

        pre_delete.connect(before_user_deleted, sender=get_user_model(), dispatch_uid="parties_abandonnees")
