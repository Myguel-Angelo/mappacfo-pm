from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from mappas.models import Mappa


@admin.register(Mappa)
class MappaAdmin(SimpleHistoryAdmin):
    list_display = ["titulo", "gerado_em", "gerado_por", "publicado"]
    list_filter = ["publicado"]
    # O arquivo e as anotações só mudam pelo serviço de geração.
    readonly_fields = ["arquivo", "gerado_por", "gerado_em", "anotacoes"]
