"""Utilidades para migrações de dados."""

from django.contrib.auth.management import create_permissions


def criar_permissoes(apps):
    # Num banco novo as permissões só existem depois do post_migrate; aqui elas são
    # criadas antes, para a migração conseguir ligá-las aos grupos.
    for app_config in apps.get_app_configs():
        app_config.models_module = True
        create_permissions(app_config, apps=apps, verbosity=0)
        app_config.models_module = None


def dar_permissoes(apps, grupos: dict[str, list[str]], app_label: str):
    """Adiciona as permissões (codenames de `app_label`) a cada grupo."""
    criar_permissoes(apps)
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    for nome, codenames in grupos.items():
        grupo = Group.objects.get(name=nome)
        grupo.permissions.add(
            *Permission.objects.filter(content_type__app_label=app_label, codename__in=codenames)
        )


def tirar_permissoes(apps, grupos: dict[str, list[str]], app_label: str):
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    for nome, codenames in grupos.items():
        grupo = Group.objects.filter(name=nome).first()
        if grupo:
            grupo.permissions.remove(
                *Permission.objects.filter(
                    content_type__app_label=app_label, codename__in=codenames
                )
            )
