"""Nome de guerra: como é guardado, como vira chave de login e como se compara.

Cadetes entram com "CAD " + nome de guerra; os demais, só com o nome de guerra. O prefixo
não é guardado: ele só diz, no login, em que grupo procurar.
"""

import re
import unicodedata

PREFIXO_CADETE = "CAD"
# "CAD" seguido de algo que não é letra nem número: "CAD BRUNO", "cad.bruno", "CAD-BRUNO".
# "CADU" não é prefixo.
_PREFIXO = re.compile(rf"^{PREFIXO_CADETE}(?![A-Z0-9])")


def _maiusculo_sem_acento(texto: str) -> str:
    decomposto = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in decomposto if not unicodedata.combining(c)).upper().strip()


def chave(texto: str) -> str:
    """Forma de comparar: sem acento, caixa, espaço e pontuação. "Ten. Cássio" → "TENCASSIO"."""
    return re.sub(r"[^A-Z0-9]", "", _maiusculo_sem_acento(texto))


def separar_prefixo(texto: str) -> tuple[bool, str]:
    """(é cadete, resto): "CAD Bruno" → (True, " BRUNO")."""
    normalizado = _maiusculo_sem_acento(texto)
    achou = _PREFIXO.match(normalizado)
    if achou:
        return True, normalizado[achou.end() :]
    return False, normalizado


def limpar(texto: str) -> str:
    """Como o nome de guerra é guardado: sem espaços sobrando e sem o CAD, que é só do
    login (a planilha pode vir com "CAD BRUNO")."""
    # NFC: "Cád" com o acento separado teria 4 caracteres e o corte do CAD erraria.
    texto = " ".join(unicodedata.normalize("NFC", texto).split())
    cadete, _ = separar_prefixo(texto)
    if cadete:
        texto = texto[len(PREFIXO_CADETE) :].lstrip(" .-:")
    return texto


def um_erro(a: str, b: str) -> bool:
    """Se a e b diferem por exatamente um erro de digitação: uma letra a mais, a menos,
    trocada por outra ou duas vizinhas invertidas ("BRUNOS", "BRUN", "BRUNA", "BURNO")."""
    if a == b or abs(len(a) - len(b)) > 1:
        return False
    if len(a) == len(b):
        diferencas = [i for i in range(len(a)) if a[i] != b[i]]
        if len(diferencas) == 1:
            return True
        i, j = (diferencas + [None, None])[:2]
        return (
            len(diferencas) == 2 and j == i + 1 and a[i] == b[j] and a[j] == b[i]  # invertidas
        )
    curto, longo = sorted((a, b), key=len)
    for i in range(len(longo)):
        if longo[:i] + longo[i + 1 :] == curto:
            return True
    return False
