import pytest
from django.db import OperationalError, connection


@pytest.mark.django_db
def test_health_ok(client):
    resp = client.get("/api/health")

    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_health_banco_fora(client, monkeypatch):
    def cursor_quebrado():
        raise OperationalError("banco fora")

    monkeypatch.setattr(connection, "cursor", cursor_quebrado)

    resp = client.get("/api/health")

    assert resp.status_code == 503
    assert resp.json() == {"status": "indisponivel"}
