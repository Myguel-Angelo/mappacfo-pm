from django.contrib.auth.management import create_permissions
from django.db import migrations

# Permissões de cada grupo. As de domínio (anotar, despachar, exportar) entram na fase 3.
GRUPOS = {
    "Cadete": [],
    "Oficial": [],
    "Comandante": [],
    "Administrador": [("contas", "gerenciar_usuarios")],
}


def criar_permissoes(apps):
    # Num banco novo as permissões só existem depois do post_migrate; aqui elas são
    # criadas antes, para a migração conseguir ligá-las aos grupos.
    for app_config in apps.get_app_configs():
        app_config.models_module = True
        create_permissions(app_config, apps=apps, verbosity=0)
        app_config.models_module = None


def criar_grupos(apps, schema_editor):
    criar_permissoes(apps)
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    for nome, perms in GRUPOS.items():
        grupo, _ = Group.objects.get_or_create(name=nome)
        for app_label, codename in perms:
            grupo.permissions.add(
                Permission.objects.get(content_type__app_label=app_label, codename=codename)
            )


def remover_grupos(apps, schema_editor):
    apps.get_model("auth", "Group").objects.filter(name__in=GRUPOS).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("contas", "0001_initial"),
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [migrations.RunPython(criar_grupos, remover_grupos)]
