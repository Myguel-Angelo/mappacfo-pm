from django.contrib.auth.forms import AdminUserCreationForm, UserChangeForm

from contas.models import Usuario


class UsuarioCreationForm(AdminUserCreationForm):
    class Meta(AdminUserCreationForm.Meta):
        model = Usuario
        fields = ["numerica", "nome", "turma"]


class UsuarioChangeForm(UserChangeForm):
    class Meta(UserChangeForm.Meta):
        model = Usuario
        fields = "__all__"
