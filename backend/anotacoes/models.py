from django.conf import settings
from django.db import models
from django.db.models import F, Q

# PROTECT em toda FK: o banco impede que um delete() apague histórico disciplinar.


class TipoPunicao(models.Model):
    """Pernoite, Revista, ... Substitui o texto livre "Outros" do sistema antigo."""

    nome = models.CharField(max_length=60, unique=True)
    ativo = models.BooleanField(default=True)

    class Meta:
        ordering = ["nome"]
        verbose_name = "tipo de punição"
        verbose_name_plural = "tipos de punição"

    def __str__(self):
        return self.nome


class TipoAnotacao(models.TextChoices):
    POSITIVA = "positiva", "Positiva"
    NEGATIVA = "negativa", "Negativa"


class StatusAnotacao(models.TextChoices):
    NOTIFICADA = "notificada", "Notificada"
    DESPACHADA = "despachada", "Despachada"
    COMPENSADA = "compensada", "Compensada"
    CUMPRIDA = "cumprida", "Cumprida"
    ARQUIVADA = "arquivada", "Arquivada"
    ANULADA = "anulada", "Anulada"


class Anotacao(models.Model):
    Tipo = TipoAnotacao
    Status = StatusAnotacao

    tipo = models.CharField(max_length=10, choices=Tipo)
    motivo = models.TextField()
    cadete = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="anotacoes"
    )
    autor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="anotacoes_feitas"
    )
    status = models.CharField(max_length=12, choices=Status, default=Status.NOTIFICADA)
    criada_em = models.DateTimeField(auto_now_add=True)

    anulada_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="anotacoes_anuladas",
    )
    anulada_em = models.DateTimeField(null=True, blank=True)
    motivo_anulacao = models.TextField(blank=True)

    class Meta:
        ordering = ["-criada_em"]
        verbose_name = "anotação"
        verbose_name_plural = "anotações"
        permissions = [
            ("anotar", "Pode anotar cadetes"),
            ("ver_anotacoes", "Pode consultar as anotações de todos os cadetes"),
            ("despachar", "Pode despachar, compensar e anular anotações"),
            ("exportar", "Pode exportar e publicar o mappa"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(tipo__in=TipoAnotacao.values), name="anotacao_tipo_valido"
            ),
            models.CheckConstraint(
                condition=Q(status__in=StatusAnotacao.values), name="anotacao_status_valido"
            ),
            models.CheckConstraint(
                condition=~Q(cadete=F("autor")), name="anotacao_autor_diferente_do_cadete"
            ),
            # Anulada <=> tem quem anulou, quando e por quê.
            models.CheckConstraint(
                condition=(
                    Q(status="anulada", anulada_por__isnull=False, anulada_em__isnull=False)
                    & ~Q(motivo_anulacao="")
                )
                | (~Q(status="anulada") & Q(anulada_por__isnull=True, anulada_em__isnull=True)),
                name="anotacao_anulacao_completa",
            ),
        ]
        indexes = [models.Index(fields=["status", "tipo"])]

    def __str__(self):
        return f"{self.get_tipo_display()} #{self.pk} — {self.cadete}"


class Despacho(models.Model):
    anotacao = models.OneToOneField(Anotacao, on_delete=models.PROTECT, related_name="despacho")
    punicao = models.ForeignKey(TipoPunicao, on_delete=models.PROTECT, related_name="despachos")
    data_cumprimento = models.DateField()
    despachado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="despachos_feitos"
    )
    despachado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["data_cumprimento"])]

    def __str__(self):
        return f"{self.punicao} em {self.data_cumprimento:%d/%m/%Y}"


class Compensacao(models.Model):
    """Positiva que anula uma negativa pendente do mesmo cadete."""

    positiva = models.OneToOneField(Anotacao, on_delete=models.PROTECT, related_name="compensa")
    negativa = models.OneToOneField(
        Anotacao, on_delete=models.PROTECT, related_name="compensada_por"
    )
    feita_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="compensacoes_feitas"
    )
    feita_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "compensação"
        verbose_name_plural = "compensações"
        constraints = [
            models.CheckConstraint(
                condition=~Q(positiva=F("negativa")), name="compensacao_anotacoes_distintas"
            ),
        ]

    def __str__(self):
        return f"#{self.positiva_id} compensa #{self.negativa_id}"
