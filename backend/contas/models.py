from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models


class Turma(models.Model):
    nome = models.CharField(max_length=40, unique=True)
    ano_ingresso = models.PositiveSmallIntegerField()
    ativa = models.BooleanField(default=True)

    class Meta:
        ordering = ["-ano_ingresso", "nome"]

    def __str__(self):
        return self.nome


GRUPO_CADETE = "Cadete"


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
    email = models.EmailField(blank=True)
    turma = models.ForeignKey(
        Turma, null=True, blank=True, on_delete=models.PROTECT, related_name="usuarios"
    )
    deve_trocar_senha = models.BooleanField(default=True)

    objects = UsuarioManager()

    USERNAME_FIELD = "numerica"
    EMAIL_FIELD = "email"
    REQUIRED_FIELDS = ["nome"]

    class Meta:
        ordering = ["nome"]
        permissions = [("gerenciar_usuarios", "Pode gerenciar usuários e turmas")]

    def __str__(self):
        return f"{self.numerica} — {self.nome}"

    def get_full_name(self):
        return self.nome

    def get_short_name(self):
        return self.nome.split(" ")[0] if self.nome else self.numerica
