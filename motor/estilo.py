"""Le o estilo.json uma vez so. Cores, fontes, tempos e zonas vem daqui; nada fica fixo no codigo."""
import json
from functools import lru_cache

from PIL import ImageFont

from motor.ambiente import RAIZ

ESTILO = json.loads((RAIZ / "estilo.json").read_text(encoding="utf-8"))
_PESOS = {100: "Thin", 200: "ExtraLight", 300: "Light", 400: "Regular", 500: "Medium",
          600: "SemiBold", 700: "Bold", 800: "ExtraBold", 900: "Black"}


def _rgb(h: str):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _mistura(frente, fundo, a):
    return tuple(round(f * a + b * (1 - a)) for f, b in zip(frente, fundo))


@lru_cache(maxsize=None)
def cor(nome: str, opacidade: float = 1.0):
    """Cor RGBA a partir do nome do papel (fundo, principal, destaque, texto, apoio), de uma derivada
    (objeto = preenchimento de objeto, pauta) ou de um HEX."""
    cores = ESTILO["cores"]
    if nome.startswith("#"):
        rgb = _rgb(nome)
    elif nome == "objeto":
        d = cores["derivadas"]["preenchimento_objeto"]
        rgb = _mistura(_rgb(cores[d["base"]]["hex"]), _rgb(cores["fundo"]["hex"]), d["opacidade"])
    elif nome == "pauta":
        d = cores["derivadas"]["pauta"]
        rgb = _mistura(_rgb(cores[d["base"]]["hex"]), _rgb(cores["fundo"]["hex"]), d["opacidade"])
    else:
        rgb = _rgb(cores[nome]["hex"])
    return (*rgb, round(255 * opacidade))


@lru_cache(maxsize=256)
def fonte(papel: str, tamanho: int):
    """Fonte do papel pedido (titulo, legenda, anotacao) no tamanho em px, ja com o peso certo."""
    f = ESTILO["fontes"][papel]
    ft = ImageFont.truetype(str(RAIZ / f["arquivo"]), max(1, int(tamanho)))
    if "variavel" in f:
        ft.set_variation_by_name(_PESOS[f["variavel"]["wght"]])
    return ft


def zona(nome: str):
    return ESTILO["zonas"][nome]
