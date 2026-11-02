import json
from datetime import timedelta

import pytest
from axes.utils import reset as axes_reset
from django.test import Client
from django.utils import timezone

from tests.factories import SENHA, TipoPunicaoFactory, UsuarioFactory


class ClienteApi:
    """Cliente que se comporta como o frontend: CSRF obrigatório, token lido do cookie."""

    def __init__(self):
        self.client = Client(enforce_csrf_checks=True)

    @property
    def cookies(self):
        return self.client.cookies

    def csrf(self):
        return self.client.get("/api/auth/csrf").json()["csrftoken"]

    def get(self, caminho):
        return self.client.get(caminho if caminho.startswith("/") else f"/api/{caminho}")

    def post(self, caminho, dados=None, *, com_csrf=True):
        return self._enviar("post", caminho, dados, com_csrf)

    def put(self, caminho, dados=None, *, com_csrf=True):
        return self._enviar("put", caminho, dados, com_csrf)

    def _enviar(self, metodo, caminho, dados, com_csrf):
        headers = {}
        if com_csrf and "csrftoken" in self.client.cookies:
            headers["X-CSRFToken"] = self.client.cookies["csrftoken"].value
        return getattr(self.client, metodo)(
            caminho if caminho.startswith("/") else f"/api/{caminho}",
            data=json.dumps(dados or {}),
            content_type="application/json",
            headers=headers,
        )

    def login(self, numerica, senha=SENHA):
        self.csrf()
        return self.post("auth/login", {"numerica": numerica, "senha": senha})


@pytest.fixture(autouse=True)
def _axes_limpo(request):
    # Sem isto, falhas de um teste contam no próximo e o resultado depende da ordem.
    usa_banco = request.node.get_closest_marker("django_db") or "db" in request.fixturenames
    if not usa_banco:
        yield
        return
    axes_reset()
    yield
    axes_reset()


@pytest.fixture
def api():
    return ClienteApi()


@pytest.fixture
def usuario(db):
    return UsuarioFactory()


@pytest.fixture
def logado(api, usuario):
    resp = api.login(usuario.numerica)
    assert resp.status_code == 200
    return api


# Domínio


@pytest.fixture
def cadete(db):
    return UsuarioFactory(cadete=True)


@pytest.fixture
def oficial(db):
    return UsuarioFactory(oficial=True)


@pytest.fixture
def comandante(db):
    return UsuarioFactory(comandante=True)


@pytest.fixture
def punicao(db):
    return TipoPunicaoFactory(nome="Pernoite")


@pytest.fixture
def hoje():
    return timezone.localdate()


@pytest.fixture
def amanha(hoje):
    return hoje + timedelta(days=1)
