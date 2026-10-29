import pytest
from django.contrib.auth.models import AnonymousUser, Group
from django.test import RequestFactory
from ninja.errors import HttpError

from contas.models import Usuario
from core.permissoes import exigir
from tests.factories import UsuarioFactory

pytestmark = pytest.mark.django_db


def test_migracao_cria_os_4_grupos():
    nomes = set(Group.objects.values_list("name", flat=True))

    assert {"Cadete", "Oficial", "Comandante", "Administrador"} <= nomes


def test_administrador_pode_gerenciar_usuarios():
    admin = Group.objects.get(name="Administrador")

    assert admin.permissions.filter(codename="gerenciar_usuarios").exists()


def test_create_user_exige_numerica():
    with pytest.raises(ValueError):
        Usuario.objects.create_user("", "x", nome="Sem numérica")


def test_superusuario_nao_precisa_trocar_senha():
    su = Usuario.objects.create_superuser("1", "Senha-forte-123", nome="Dev")

    assert su.is_staff and su.is_superuser
    assert su.deve_trocar_senha is False


def test_usuario_novo_precisa_trocar_senha():
    u = Usuario.objects.create_user("2", "Senha-forte-123", nome="Cadete")

    assert u.deve_trocar_senha is True


def _request(usuario):
    request = RequestFactory().post("/")
    request.user = usuario
    return request


def test_exigir_nega_sem_permissao():
    with pytest.raises(HttpError) as exc:
        exigir(_request(UsuarioFactory()), "contas.gerenciar_usuarios")

    assert exc.value.status_code == 403


def test_exigir_nega_anonimo():
    with pytest.raises(HttpError):
        exigir(_request(AnonymousUser()), "contas.gerenciar_usuarios")


def test_exigir_libera_com_permissao_do_grupo():
    usuario = UsuarioFactory()
    usuario.groups.add(Group.objects.get(name="Administrador"))

    exigir(_request(usuario), "contas.gerenciar_usuarios")
