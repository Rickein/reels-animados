"""Transicao entre capitulos: um rabisco grosso de caneta cobre a tela e depois se desfaz."""
import random
from functools import lru_cache

from PIL import Image, ImageDraw

from motor import tempo as T
from motor.desenho import SS, cortar, mao
from motor.estilo import ESTILO, cor

TR = ESTILO["transicao"]
QW, QH = ESTILO["quadro"]["largura"], ESTILO["quadro"]["altura"]


@lru_cache(maxsize=16)
def _caminho(semente):
    """Zigue-zague diagonal que cobre o quadro inteiro (com folga para fora)."""
    pts, y, esquerda = [], -120.0, True
    r = random.Random(semente)
    while y < QH + 200:
        pts.append((-160.0 if esquerda else QW + 160.0, y + r.uniform(-20, 20)))
        y += TR["espacamento"]
        esquerda = not esquerda
    return mao(pts, False, semente, TR["tremor_px"], 40)


def desenhar(quadro, p, semente=0):
    """p de 0 a 1: na primeira metade o rabisco cobre; na segunda, vai sumindo pelo comeco."""
    if p <= 0 or p >= 1:
        return
    caminho = _caminho(semente)
    if p < 0.5:
        trecho = cortar(caminho, False, T.in_out(p / 0.5))
    else:
        inteiro = cortar(caminho, False, 1.0)
        corte = cortar(caminho, False, T.in_out((p - 0.5) / 0.5))
        trecho = [corte[-1]] + inteiro[len(corte) - 1:]
    if len(trecho) < 2:
        return
    mascara = Image.new("L", (QW * SS, QH * SS))  # desenha em 2x e reduz: borda do rabisco sem serrilhado
    k = SS
    d = ImageDraw.Draw(mascara)
    w = round(TR["largura_traco"] * k)
    pts = [(x * k, y * k) for x, y in trecho]
    d.line(pts, fill=255, width=w, joint="curve")
    for x, y in (pts[0], pts[-1]):
        d.ellipse([x - w / 2, y - w / 2, x + w / 2, y + w / 2], fill=255)
    if mascara.size != (QW, QH):
        mascara = mascara.resize((QW, QH), Image.BOX)
    tinta = Image.new("RGBA", (QW, QH), cor(TR["cor"]))
    tinta.putalpha(mascara)
    quadro.alpha_composite(tinta)
