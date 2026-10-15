from django.apps import AppConfig
from django.db.models.signals import post_migrate


class CoreConfig(AppConfig):
    name = 'core'

    def ready(self):
        from .permissions import sync_role_groups

        post_migrate.connect(sync_role_groups, dispatch_uid="core.sync_role_groups")
