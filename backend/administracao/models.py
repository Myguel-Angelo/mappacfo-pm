import uuid
from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone

VALIDADE_PREVIA = timedelta(minutes=30)


class ImportacaoCadetes(models.Model):
    """Prévia de uma importação: o que cada linha da planilha vai fazer.

    Nada é gravado em usuários até a confirmação. Senhas não ficam aqui: as temporárias
    só existem na resposta da confirmação.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    criada_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="importacoes"
    )
    criada_em = models.DateTimeField(auto_now_add=True)
    nome_arquivo = models.CharField(max_length=255)
    atualizar_existentes = models.BooleanField(default=False)
    criar_turmas = models.BooleanField(default=False)
    linhas = models.JSONField(default=list)
    confirmada_em = models.DateTimeField(null=True, blank=True)
    resumo = models.JSONField(null=True, blank=True)  # contagens; nunca senhas

    class Meta:
        ordering = ["-criada_em"]
        verbose_name = "importação de cadetes"
        verbose_name_plural = "importações de cadetes"

    def __str__(self):
        return f"{self.nome_arquivo} ({self.criada_em:%d/%m/%Y %H:%M})"

    @property
    def expira_em(self):
        return self.criada_em + VALIDADE_PREVIA

    @property
    def expirada(self):
        return timezone.now() >= self.expira_em
