from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from simple_history.models import HistoricalRecords

from contas import nome_guerra as ng


class Turma(models.Model):
    nome = models.CharField(max_length=40, unique=True)
    ano_ingresso = models.PositiveSmallIntegerField()
    ativa = models.BooleanField(default=True)
    history = HistoricalRecords()

    class Meta:
        ordering = ["-ano_ingresso", "nome"]

    def __str__(self):
        return self.nome


GRUPO_CADETE = "Cadete"


class HistoricoDeUsuario(HistoricalRecords):
    """Histórico que ignora o save do login (só last_login, que fica fora do histórico):
    sem isto, cada login viraria uma linha vazia na auditoria."""

    def post_save(self, instance, created, using=None, **kwargs):
        if kwargs.get("update_fields") == frozenset({"last_login"}):
            return
        super().post_save(instance, created, using=using, **kwargs)


# Como cada grupo aparece na tela ("Oficial Comandante Fulano"), na ordem de prioridade.
# Só exibição: o que o usuário pode fazer vem das permissões, nunca do nome do grupo.
PERFIS = [
    ("Comandante", "Oficial Comandante"),
    ("Oficial", "Oficial"),
    ("Administrador", "Administrador"),
    (GRUPO_CADETE, "Cadete"),
]


class UsuarioManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, numerica, password=None, **extra):
        if not numerica:
            raise ValueError("A numérica é obrigatória.")
        usuario = self.model(numerica=numerica, **extra)
        usuario.set_password(password)
        usuario.save(using=self._db)
        return usuario

    def create_superuser(self, numerica, password=None, **extra):
        extra.setdefault("is_staff", True)
        extra.setdefault("is_superuser", True)
        extra.setdefault("deve_trocar_senha", False)
        if not extra["is_staff"] or not extra["is_superuser"]:
            raise ValueError("Superusuário precisa de is_staff e is_superuser.")
        return self.create_user(numerica, password, **extra)

    def cadetes(self):
        """Cadetes ativos. Ser cadete é identidade (grupo); o que cada um pode fazer são
        permissões."""
        return self.filter(is_active=True, groups__name=GRUPO_CADETE)


class Usuario(AbstractUser):
    # Login pela numérica; o nome completo fica num campo só.
    username = None
    first_name = None
    last_name = None

    numerica = models.CharField(max_length=20, unique=True)
    nome = models.CharField(max_length=120)
    # O login é pelo nome de guerra (cadetes com "CAD " na frente). A chave é a forma
    # normalizada (sem acento, caixa, espaço e pontuação): é por ela que o login procura, e
    # é ela que não pode repetir, então "Ten. Cássio" e "TEN CASSIO" são o mesmo nome.
    nome_guerra = models.CharField("nome de guerra", max_length=40)
    # NULL (e não "") quando não há nome de guerra: dois vazios não podem colidir no unique.
    chave_login = models.CharField(max_length=40, unique=True, null=True, editable=False)  # noqa: DJ001
    email = models.EmailField(blank=True)
    turma = models.ForeignKey(
        Turma, null=True, blank=True, on_delete=models.PROTECT, related_name="usuarios"
    )
    deve_trocar_senha = models.BooleanField(default=True)
    # Auditoria (fase 6): grupos entram como m2m; hash de senha e último login ficam fora.
    history = HistoricoDeUsuario(
        excluded_fields=["password", "last_login", "chave_login"], m2m_fields=["groups"]
    )

    objects = UsuarioManager()

    USERNAME_FIELD = "numerica"
    EMAIL_FIELD = "email"
    REQUIRED_FIELDS = ["nome", "nome_guerra"]

    class Meta:
        ordering = ["nome"]
        permissions = [("gerenciar_usuarios", "Pode gerenciar usuários e turmas")]

    def __str__(self):
        return f"{self.numerica} — {self.nome}"

    def save(self, *args, **kwargs):
        self.nome_guerra = ng.limpar(self.nome_guerra)
        self.chave_login = ng.chave(self.nome_guerra) or None
        campos = kwargs.get("update_fields")
        if campos is not None and "nome_guerra" in campos:
            kwargs["update_fields"] = {*campos, "chave_login"}
        super().save(*args, **kwargs)

    @property
    def eh_cadete(self):
        return any(g.name == GRUPO_CADETE for g in self.groups.all())

    @property
    def texto_login(self):
        """O que a pessoa digita para entrar: "CAD BRUNO" (cadete) ou "TEN CÁSSIO"."""
        return f"{ng.PREFIXO_CADETE} {self.nome_guerra}" if self.eh_cadete else self.nome_guerra

    @property
    def perfil(self):
        # groups.all() aproveita o prefetch_related("groups") das listagens.
        grupos = {g.name for g in self.groups.all()}
        return next((rotulo for grupo, rotulo in PERFIS if grupo in grupos), "")

    def get_full_name(self):
        return self.nome

    def get_short_name(self):
        return self.nome.split(" ")[0] if self.nome else self.numerica
