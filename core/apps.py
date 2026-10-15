from django.apps import AppConfig
from django.db.models.signals import post_migrate


class CoreConfig(AppConfig):
    name = 'core'

    def ready(self):
        from .permissions import sync_officer_group

        post_migrate.connect(sync_officer_group, dispatch_uid="core.sync_officer_group")
