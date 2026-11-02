from uuid import uuid4

from django.conf import settings
from django.db import models
from django.utils import timezone
from simple_history.models import HistoricalRecords

from anotacoes.models import Anotacao
from mappas.storage import storage_privado


def caminho_mappa(instance, filename):
    # O nome no disco nunca vem do usuário: no sistema antigo, "MAPA N°014/2026" virou pasta.
    return f"mappas/{timezone.localdate():%Y/%m}/{uuid4().hex}.xlsx"


class Mappa(models.Model):
    titulo = models.CharField(max_length=120)  # o que o comandante digitou; só no banco
    arquivo = models.FileField(storage=storage_privado, upload_to=caminho_mappa)
    gerado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="mappas_gerados"
    )
    gerado_em = models.DateTimeField(auto_now_add=True)
    publicado = models.BooleanField(default=False)
    anotacoes = models.ManyToManyField(Anotacao, related_name="mappas")
    history = HistoricalRecords()

    class Meta:
        ordering = ["-gerado_em"]

    def __str__(self):
        return self.titulo
