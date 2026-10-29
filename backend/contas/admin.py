from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from contas.forms import UsuarioChangeForm, UsuarioCreationForm
from contas.models import Turma, Usuario


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    form = UsuarioChangeForm
    add_form = UsuarioCreationForm
    ordering = ["nome"]
    list_display = ["numerica", "nome", "turma", "is_active", "deve_trocar_senha"]
    list_filter = ["is_active", "groups", "turma"]
    search_fields = ["numerica", "nome", "email"]
    fieldsets = [
        (None, {"fields": ["numerica", "password"]}),
        ("Dados", {"fields": ["nome", "email", "turma", "deve_trocar_senha"]}),
        (
            "Permissões",
            {"fields": ["is_active", "is_staff", "is_superuser", "groups", "user_permissions"]},
        ),
        ("Datas", {"fields": ["last_login", "date_joined"]}),
    ]
    add_fieldsets = [
        (
            None,
            {
                "classes": ["wide"],
                "fields": [
                    "numerica",
                    "nome",
                    "turma",
                    "usable_password",
                    "password1",
                    "password2",
                ],
            },
        ),
    ]


@admin.register(Turma)
class TurmaAdmin(admin.ModelAdmin):
    list_display = ["nome", "ano_ingresso", "ativa"]
    list_filter = ["ativa"]
