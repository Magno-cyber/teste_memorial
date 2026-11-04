from django.apps import AppConfig
from django.db.models.signals import post_migrate


def _criar_grupo_administrativo(sender, **kwargs):
    """Grupo pronto para o administrativo: vê as entradas e saídas, sem poder alterar conteúdo."""
    from django.contrib.auth.models import Group, Permission
    from django.db import connection

    if Group._meta.db_table not in connection.introspection.table_names():
        return  # migração parcial, antes das tabelas do auth

    grupo, _ = Group.objects.get_or_create(name="Administrativo")
    grupo.permissions.add(*Permission.objects.filter(content_type__app_label="memorial", codename="view_registro"))


class MemorialConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "memorial"
    verbose_name = "Memorial"

    def ready(self):
        from . import signals  # noqa: F401

        post_migrate.connect(_criar_grupo_administrativo, sender=self)
