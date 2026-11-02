import os

from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.utils.deconstruct import deconstructible


@deconstructible
class StoragePrivado(FileSystemStorage):
    """Arquivos que só saem por view autenticada (o mappa).

    Fica fora do MEDIA_ROOT e não tem URL: storage.url() levanta erro, então nenhum código
    consegue gerar link público por engano. O local vem do setting a cada uso, o que deixa
    os testes trocarem a pasta com o fixture `settings`.
    """

    @property
    def base_location(self):
        return settings.PRIVATE_STORAGE_ROOT

    @property
    def location(self):
        return os.path.abspath(self.base_location)

    @property
    def base_url(self):
        return None


storage_privado = StoragePrivado()
