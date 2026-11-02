"""URLconf de teste com uma rota que usa a auth padrão (as de domínio chegam na fase 3)."""

from django.urls import path
from ninja import NinjaAPI

from config.urls import urlpatterns as urls_base
from core.auth import sessao
from core.erros import instalar_handlers

api_teste = NinjaAPI(auth=sessao, urls_namespace="api-teste")
instalar_handlers(api_teste)


@api_teste.get("/protegida")
def protegida(request):
    return {"ok": True}


urlpatterns = [*urls_base, path("api-teste/", api_teste.urls)]
