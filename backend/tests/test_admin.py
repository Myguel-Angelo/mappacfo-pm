import pytest

from contas.models import Usuario

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize(
    "url",
    ["/admin/contas/usuario/", "/admin/contas/usuario/add/", "/admin/contas/turma/add/"],
)
def test_paginas_do_admin_abrem(admin_client, url):
    assert admin_client.get(url).status_code == 200


def test_editar_usuario_no_admin_abre(admin_client, admin_user):
    assert admin_client.get(f"/admin/contas/usuario/{admin_user.pk}/change/").status_code == 200


def test_criar_usuario_pelo_admin(admin_client):
    senha = "Senha-forte-admin-1"
    resp = admin_client.post(
        "/admin/contas/usuario/add/",
        {
            "numerica": "777",
            "nome": "Via Admin",
            "usable_password": "true",
            "password1": senha,
            "password2": senha,
        },
    )

    assert resp.status_code == 302
    criado = Usuario.objects.get(numerica="777")
    assert criado.check_password(senha)
    assert criado.deve_trocar_senha is True
