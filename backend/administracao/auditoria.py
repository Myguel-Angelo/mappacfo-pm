"""Auditoria: os históricos do simple-history unidos numa linha do tempo só.

Cada modelo tem sua tabela de histórico. Para a página N (mais recentes primeiro), basta
pegar as N * tamanho linhas mais recentes de cada tabela, intercalar por data e recortar a
página: nenhuma consulta traz a tabela inteira, e o índice de history_date de cada uma
resolve a ordenação.
"""

import heapq
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

from django.conf import settings
from django.contrib.auth.models import Group
from django.utils import timezone

from anotacoes.models import Anotacao, Compensacao, Despacho, TipoPunicao
from contas.models import Turma, Usuario
from mappas.models import Mappa

POR_PAGINA = settings.NINJA_PAGINATION_PER_PAGE

ACOES = {"+": "criou", "~": "alterou", "-": "apagou"}


@dataclass(frozen=True)
class Fonte:
    rotulo: str
    modelo: type
    relacionados: tuple[str, ...]
    descrever: object  # (registro histórico) -> str


FONTES = {
    "anotacao": Fonte(
        "Anotação",
        Anotacao,
        ("cadete",),
        lambda h: (
            f"Anotação #{h.id} ({h.get_tipo_display().lower()}) do cadete "
            f"{h.cadete.numerica} — {h.cadete.nome}"
        ),
    ),
    "despacho": Fonte(
        "Despacho", Despacho, ("punicao",), lambda h: f"Despacho da anotação #{h.anotacao_id}"
    ),
    "compensacao": Fonte(
        "Compensação",
        Compensacao,
        (),
        lambda h: f"Positiva #{h.positiva_id} compensa negativa #{h.negativa_id}",
    ),
    "mappa": Fonte("Mappa", Mappa, (), lambda h: f'Mappa "{h.titulo}"'),
    "usuario": Fonte("Usuário", Usuario, (), lambda h: f"Usuário {h.numerica} — {h.nome}"),
    "turma": Fonte("Turma", Turma, (), lambda h: f"Turma {h.nome}"),
    "punicao": Fonte("Tipo de punição", TipoPunicao, (), lambda h: f"Tipo de punição {h.nome}"),
}


def _consulta(fonte: Fonte, filtros):
    qs = fonte.modelo.history.select_related("history_user", *fonte.relacionados)
    if filtros.inicio:
        qs = qs.filter(history_date__gte=_inicio_do_dia(filtros.inicio))
    if filtros.fim:
        qs = qs.filter(history_date__lt=_inicio_do_dia(filtros.fim) + timedelta(days=1))
    if filtros.usuario_id is not None:
        qs = qs.filter(history_user_id=filtros.usuario_id)
    return qs.order_by("-history_date", "-history_id")


def _inicio_do_dia(dia: date) -> datetime:
    return timezone.make_aware(datetime.combine(dia, time.min))


# Mudanças


class Nomes:
    """Nome legível de chaves estrangeiras (turma, punição, usuário, grupo), com cache por
    página para não repetir consultas."""

    def __init__(self):
        self._cache: dict[tuple[type, object], str] = {}

    def de(self, modelo, pk) -> str:
        chave = (modelo, pk)
        if chave not in self._cache:
            objeto = modelo._default_manager.filter(pk=pk).first()
            if objeto is None:
                self._cache[chave] = f"#{pk}"
            elif modelo is Usuario:
                self._cache[chave] = f"{objeto.numerica} — {objeto.nome}"
            else:
                self._cache[chave] = getattr(objeto, "nome", None) or getattr(
                    objeto, "name", str(objeto)
                )
        return self._cache[chave]


def _valor(campo, valor, nomes: Nomes) -> str:
    if valor is None or valor == "":
        return "—"
    if isinstance(valor, bool):
        return "sim" if valor else "não"
    if isinstance(valor, list):  # m2m (grupos do usuário)
        return ", ".join(sorted(nomes.de(Group, item.get("group")) for item in valor)) or "—"
    if campo is not None and campo.is_relation and campo.related_model is not None:
        return nomes.de(campo.related_model, valor)
    if campo is not None and campo.choices:
        return str(dict(campo.flatchoices).get(valor, valor))
    if isinstance(valor, datetime):
        return f"{timezone.localtime(valor):%d/%m/%Y %H:%M}"
    if isinstance(valor, date):
        return f"{valor:%d/%m/%Y}"
    return str(valor)


def _mudancas(registro, nomes: Nomes) -> list[dict]:
    anterior = registro.prev_record
    if registro.history_type != "~" or anterior is None:
        return []
    modelo = registro.instance_type
    mudancas = []
    for mudanca in registro.diff_against(anterior, foreign_keys_are_objs=False).changes:
        try:
            campo = modelo._meta.get_field(mudanca.field)
            rotulo = str(campo.verbose_name)
        except Exception:  # noqa: BLE001 - campo removido do modelo depois do registro
            campo, rotulo = None, mudanca.field
        mudancas.append(
            {
                "campo": rotulo,
                "de": _valor(campo, mudanca.old, nomes),
                "para": _valor(campo, mudanca.new, nomes),
            }
        )
    return mudancas


def _item(tipo: str, registro, nomes: Nomes) -> dict:
    fonte = FONTES[tipo]
    autor = registro.history_user
    return {
        "id": f"{tipo}-{registro.history_id}",
        "quando": registro.history_date,
        "usuario": autor,
        "acao": ACOES[registro.history_type],
        "tipo": tipo,
        "tipo_rotulo": fonte.rotulo,
        "registro_id": registro.id,
        "descricao": fonte.descrever(registro),
        "motivo": registro.history_change_reason or None,
        "mudancas": _mudancas(registro, nomes),
    }


def _fluxo(tipo, registros):
    # Função (e não gerador aninhado no list comprehension): o `tipo` fica fixo em cada fluxo.
    for registro in registros:
        yield registro.history_date, registro.history_id, tipo, registro


def linha_do_tempo(filtros) -> dict:
    tipos = [filtros.tipo] if filtros.tipo else list(FONTES)
    pagina = max(filtros.page, 1)
    limite = pagina * POR_PAGINA

    consultas = {tipo: _consulta(FONTES[tipo], filtros) for tipo in tipos}
    total = sum(qs.count() for qs in consultas.values())
    fluxos = [_fluxo(tipo, qs[:limite]) for tipo, qs in consultas.items()]
    intercalados = heapq.merge(*fluxos, key=lambda item: (item[0], item[1]), reverse=True)
    recorte = list(intercalados)[(pagina - 1) * POR_PAGINA : limite]

    nomes = Nomes()
    return {
        "items": [_item(tipo, registro, nomes) for _, _, tipo, registro in recorte],
        "count": total,
    }
