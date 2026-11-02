from django.db import DatabaseError, connection
from ninja import NinjaAPI, Schema, Status

from administracao.api import router as admin_router
from anotacoes.api import router as anotacoes_router
from contas.api import router as auth_router
from core.auth import sessao
from core.erros import instalar_handlers
from mappas.api import router as mappas_router

# Toda rota exige sessão por padrão; as públicas declaram auth=None.
api = NinjaAPI(title="MAPPA CFO", version="2.0", auth=sessao)
instalar_handlers(api)

api.add_router("/auth", auth_router)
api.add_router("/", anotacoes_router)
api.add_router("/mappas", mappas_router)
api.add_router("/admin", admin_router)


class HealthOut(Schema):
    status: str


@api.get("/health", auth=None, response={200: HealthOut, 503: HealthOut})
def health(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
    except DatabaseError:
        return Status(503, {"status": "indisponivel"})
    return Status(200, {"status": "ok"})
