from django.contrib import admin

from anotacoes.models import Anotacao, Compensacao, Despacho, TipoPunicao


@admin.register(TipoPunicao)
class TipoPunicaoAdmin(admin.ModelAdmin):
    list_display = ["nome", "ativo"]


@admin.register(Anotacao)
class AnotacaoAdmin(admin.ModelAdmin):
    list_display = ["id", "tipo", "status", "cadete", "autor", "criada_em"]
    list_filter = ["status", "tipo"]
    search_fields = ["cadete__numerica", "cadete__nome", "motivo"]
    raw_id_fields = ["cadete", "autor", "anulada_por"]
    list_select_related = ["cadete", "autor"]

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Despacho)
class DespachoAdmin(admin.ModelAdmin):
    list_display = ["anotacao", "punicao", "data_cumprimento", "despachado_por"]
    raw_id_fields = ["anotacao", "despachado_por"]

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Compensacao)
class CompensacaoAdmin(admin.ModelAdmin):
    list_display = ["positiva", "negativa", "feita_por", "feita_em"]
    raw_id_fields = ["positiva", "negativa", "feita_por"]

    def has_delete_permission(self, request, obj=None):
        return False
