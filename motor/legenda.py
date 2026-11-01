"""Legenda palavra por palavra: blocos de 1 a 4 palavras numa tira de caderno, palavra-chave com marca-texto."""
import math
import random
from functools import lru_cache

from PIL import Image, ImageChops, ImageDraw, ImageFilter

from motor import tempo as T
from motor.desenho import Desenho, Mancha, Traco, compor, render
from motor.estilo import ESTILO, cor, fonte

LEG = ESTILO["legenda"]
CAIXA, TXT, BLOCOS = LEG["caixa"], LEG["texto"], LEG["blocos"]
ENTRA, CHAVE = LEG["entrada_palavra"], LEG["palavra_chave"]
PONTUACAO_FIM = ".,;:!?…"
MARGEM = 24  # folga em volta da tira (para o tremor e a rotacao)


def limpar(texto: str) -> str:
    """Tira virgula/ponto do fim da palavra (na legenda ficam so ! e ?)."""
    return texto.rstrip(".,;:…") or texto


def montar_blocos(palavras, pausa=0.35, max_chars=24):
    blocos, atual = [], []
    for k, p in enumerate(palavras):
        if atual:
            ant = palavras[k - 1]
            chars = sum(len(x["texto"]) + 1 for x in atual) + len(p["texto"])
            if (len(atual) >= BLOCOS["palavras_max"] or chars > max_chars or ant["texto"][-1] in PONTUACAO_FIM
                    or p["inicio"] - ant["fim"] > pausa):
                blocos.append(atual)
                atual = []
        atual.append(p)
    if atual:
        blocos.append(atual)
    # uma palavra sozinha no fim de frase gruda no bloco anterior se couber
    juntos = []
    for b in blocos:
        if (juntos and len(b) == 1 and len(juntos[-1]) < BLOCOS["palavras_max"]
                and juntos[-1][-1]["texto"][-1] not in PONTUACAO_FIM
                and sum(len(x["texto"]) + 1 for x in juntos[-1]) + len(b[0]["texto"]) <= max_chars):
            juntos[-1] = juntos[-1] + b
        else:
            juntos.append(b)
    saida = []
    for i, b in enumerate(juntos):  # o bloco anterior fica ate a primeira palavra do proximo ser dita
        ini = b[0]["inicio"]
        fim = juntos[i + 1][0]["inicio"] if i + 1 < len(juntos) else b[-1]["fim"] + 0.6
        saida.append({"inicio": ini, "fim": fim, "palavras": b})
    return saida


@lru_cache(maxsize=8)
def _tira(semente):
    """A tira de caderno (papel, pauta, contorno tremido), sem rotacao, com MARGEM em volta."""
    w, h = CAIXA["largura"], CAIXA["altura"]
    camadas = [Mancha([(-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2)], CAIXA["cor"], deslocamento=(0, 0), tremor=1.2)]
    y = -h / 2 + CAIXA["pauta_espacamento"]
    while y < h / 2 - 10:
        camadas.append(Traco([(-w / 2 + 6, y), (w / 2 - 6, y)], cor="pauta", espessura=2, halo=False, tremor=0.8, textura=False))
        y += CAIXA["pauta_espacamento"]
    camadas.append(Traco([(-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2)], cor=CAIXA["contorno"],
                         espessura=CAIXA["espessura_contorno"], fechado=True, halo=False))
    img, (ox, oy) = render(Desenho(camadas), semente=semente)
    tela = Image.new("RGBA", (w + 2 * MARGEM, h + 2 * MARGEM))
    compor(tela, img, round(MARGEM + w / 2 - ox), round(MARGEM + h / 2 - oy))
    return tela


@lru_cache(maxsize=512)
def _palavra(texto, tamanho):
    f = fonte(TXT["fonte"], tamanho)
    l, t, r, b = f.getbbox(texto, anchor="ls")
    img = Image.new("RGBA", (r - l + 8, b - t + 8))
    ImageDraw.Draw(img).text((4 - l, 4 - t), texto, font=f, fill=cor(TXT["cor"]), anchor="ls")
    return img, (4 - l, 4 - t)  # (x, y) da linha de base dentro da imagem


@lru_cache(maxsize=256)
def _diagramar(textos, largura_max=None, papel=None, tamanhos=None):
    """Escolhe o tamanho e quebra em ate 2 linhas; devolve posicoes (x da palavra, y da linha de base)."""
    largura_max = largura_max or TXT["largura_max"]
    for tam in tamanhos or TXT["tamanhos"]:
        f = fonte(papel or TXT["fonte"], tam)
        esp = f.getlength(" ")
        linhas, atual, larg = [[]], 0.0, 0.0
        for i, tx in enumerate(textos):
            lw = f.getlength(tx)
            if linhas[-1] and atual + esp + lw > largura_max:
                linhas.append([])
                atual = 0.0
            atual += (esp if linhas[-1] else 0) + lw
            linhas[-1].append((i, lw))
        if len(linhas) <= TXT["linhas_max"] and all(sum(w for _, w in l) + esp * (len(l) - 1) <= largura_max for l in linhas):
            break
    entre = tam * TXT["entrelinha"]
    topo = -(len(linhas) * entre) / 2 + entre * 0.78  # linha de base da primeira linha (bloco centrado)
    pos = {}
    for li, linha in enumerate(linhas):
        largura_linha = sum(w for _, w in linha) + esp * (len(linha) - 1)
        x = -largura_linha / 2
        for i, lw in linha:
            pos[i] = (x, topo + li * entre, lw)
            x += lw + esp
    return tam, pos


class Legenda:
    def __init__(self, palavras, chaves=(), sempre_visivel=True):
        self.blocos = montar_blocos(palavras)
        self.chaves = {palavras[i]["inicio"] for i in chaves}
        self.sempre_visivel = sempre_visivel

    def bloco_em(self, t):
        for b in self.blocos:
            if b["inicio"] <= t < b["fim"]:
                return b
        return None

    def desenhar(self, quadro, t):
        bloco = self.bloco_em(t)
        if not bloco and not self.sempre_visivel:
            return None
        semente = T.fervura(t, 5)
        tela = _tira(semente).copy()
        ccx, ccy = tela.width / 2, tela.height / 2
        if bloco:
            textos = tuple(limpar(p["texto"]) for p in bloco["palavras"])
            tam, pos = _diagramar(textos)
            marca = Image.new("RGB", tela.size, (255, 255, 255))
            dm = ImageDraw.Draw(marca)
            palavras_img = []
            for i, p in enumerate(bloco["palavras"]):
                u = t - p["inicio"]
                if u < 0:
                    continue
                x, base, lw = pos[i]
                if p["inicio"] in self.chaves:  # marca-texto passando por tras
                    k = T.in_out(T.progresso(u, CHAVE["atraso"], CHAVE["duracao"]))
                    if k > 0:
                        f = CHAVE["folga_px"]
                        topo, baixo = ccy + base - tam * 0.78, ccy + base + tam * 0.16
                        dm.rectangle([ccx + x - f, topo, ccx + x - f + (lw + 2 * f) * k, baixo], fill=cor(CHAVE["cor"])[:3])
                palavras_img.append((i, p, u, x, base))
            tela = Image.merge("RGBA", (*ImageChops.multiply(tela.convert("RGB"), marca).split(), tela.getchannel("A")))
            for i, p, u, x, base in palavras_img:
                img, (bx, by) = _palavra(textos[i], tam)
                a = T.progresso(u, 0, ENTRA["duracao"])
                esc = ENTRA["escala_inicial"] + (1 - ENTRA["escala_inicial"]) * T.back_out(a, ENTRA["passada"])
                rot = (random.Random(round(p["inicio"] * 1000)).random() * 2 - 1) * ENTRA["rotacao_max_graus"] * (1 - a * 0.6)
                alfa = T.clamp(a * 5)
                cx, cy = ccx + x - bx + img.width / 2, ccy + base - by + img.height / 2
                im = img
                if esc != 1 or rot:
                    im = im.resize((max(1, round(img.width * esc)), max(1, round(img.height * esc))), Image.BILINEAR)
                    im = im.rotate(-rot, resample=Image.BILINEAR, expand=True)
                if alfa < 1:
                    im = im.copy()
                    im.putalpha(im.getchannel("A").point(lambda v: round(v * alfa)))
                compor(tela, im, round(cx - im.width / 2), round(cy - im.height / 2))
        girada = tela.rotate(-CAIXA["rotacao_graus"], resample=Image.BILINEAR, expand=True)
        cx, cy = CAIXA["centro"]
        compor(quadro, girada, round(cx - girada.width / 2), round(cy - girada.height / 2))
        return (cx - girada.width / 2, cy - girada.height / 2, cx + girada.width / 2, cy + girada.height / 2)


def _mistura_cor(a, b, k):
    return tuple(round(x + (y - x) * k) for x, y in zip(a, b))


class LegendaSimples(Legenda):
    """Variante sem tira: o bloco aparece inteiro numa cor clara e cada palavra fica na cor_falada quando e dita."""

    def __init__(self, palavras, chaves=(), sempre_visivel=False, variante="simples"):
        super().__init__(palavras, chaves, sempre_visivel)
        self.v = LEG["variantes"][variante]

    def desenhar(self, quadro, t):
        bloco = self.bloco_em(t)
        if not bloco:
            return None
        v = self.v
        textos = tuple(limpar(p["texto"]) for p in bloco["palavras"])
        tam, pos = _diagramar(textos, v["largura_max"], v["fonte"], tuple(v["tamanhos"]))
        f = fonte(v["fonte"], tam)
        larg = v["largura_max"] + 2 * MARGEM
        alt = round(v["tamanhos"][0] * TXT["entrelinha"] * TXT["linhas_max"]) + 2 * MARGEM
        tela = Image.new("RGBA", (larg, alt))
        d = ImageDraw.Draw(tela)
        ccx, ccy = larg / 2, alt / 2
        clara, falada = cor(v["cor"]), cor(v["cor_falada"])
        for i, p in enumerate(bloco["palavras"]):
            x, base, lw = pos[i]
            u = t - p["inicio"]
            k = T.in_out(T.progresso(u, 0, v["troca_cor"])) if u >= 0 else 0.0
            c = _mistura_cor(clara, falada, k)
            esc = 1.0
            if 0 <= u < v["pulo_duracao"]:
                esc = 1 + (v["pulo_escala"] - 1) * math.sin(math.pi * u / v["pulo_duracao"])
            if esc == 1.0:
                d.text((ccx + x, ccy + base), textos[i], font=f, fill=c, anchor="ls")
            else:
                img, (bx, by) = _palavra_cor(textos[i], tam, c, v["fonte"])
                im = img.resize((round(img.width * esc), round(img.height * esc)), Image.BILINEAR)
                cx, cy = ccx + x - bx + img.width / 2, ccy + base - by + img.height / 2
                compor(tela, im, round(cx - im.width / 2), round(cy - im.height / 2))
        s = v["sombra"]
        if s["opacidade"] > 0:
            sombra = Image.new("RGBA", tela.size, (0, 0, 0, 0))
            sombra.putalpha(tela.getchannel("A").point(lambda a: round(a * s["opacidade"])))
            sombra = sombra.filter(ImageFilter.GaussianBlur(s["desfoque"]))
            base_img = Image.new("RGBA", tela.size)
            base_img.alpha_composite(sombra, tuple(s["deslocamento"]))
            base_img.alpha_composite(tela)
            tela = base_img
        cx, cy = v["centro"]
        x0, y0 = round(cx - larg / 2), round(cy - alt / 2)
        compor(quadro, tela, x0, y0)
        return (x0, y0, x0 + larg, y0 + alt)


@lru_cache(maxsize=512)
def _palavra_cor(texto, tamanho, c, papel):
    f = fonte(papel, tamanho)
    l, t, r, b = f.getbbox(texto, anchor="ls")
    img = Image.new("RGBA", (r - l + 8, b - t + 8))
    ImageDraw.Draw(img).text((4 - l, 4 - t), texto, font=f, fill=c, anchor="ls")
    return img, (4 - l, 4 - t)


def criar(palavras, chaves, opcoes):
    """Legenda pedida nas opcoes do roteiro (padrao: tira de caderno)."""
    variante = opcoes.get("legenda")
    if variante:
        return LegendaSimples(palavras, chaves, variante=variante)
    return Legenda(palavras, chaves, opcoes.get("cobrir_legenda_antiga", False))


def caixa_ocupada(opcoes):
    """(x0, y0, x1, y1) da area da legenda no quadro, conforme a variante pedida no roteiro."""
    variante = opcoes.get("legenda")
    if variante:
        v = LEG["variantes"][variante]
        cx, cy = v["centro"]
        meia_alt = v["tamanhos"][0] * TXT["entrelinha"] * TXT["linhas_max"] / 2
        return (cx - v["largura_max"] / 2, cy - meia_alt, cx + v["largura_max"] / 2, cy + meia_alt)
    cx, cy = CAIXA["centro"]
    return (cx - CAIXA["largura"] / 2, cy - CAIXA["altura"] / 2, cx + CAIXA["largura"] / 2, cy + CAIXA["altura"] / 2)
