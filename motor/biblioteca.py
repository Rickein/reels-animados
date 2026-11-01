"""Biblioteca de desenhos reaproveitaveis, todos no mesmo traco (estilo.json).

Cada desenho e uma funcao que devolve um Desenho em coordenadas locais (px na escala 1, origem no
centro). Parametros mudam o estado (ex.: pao com boina, balanca inclinada, cronometro com ponteiro).
Uso:  img, origem = obter("pao", boina=True, semente=1)
"""
import math
from functools import lru_cache

from motor.desenho import Desenho, Mancha, Texto, Traco, render
from motor.estilo import fonte

REGISTRO = {}
ANCORAS = {}   # pontos nomeados de cada desenho (onde encaixar outro desenho), na escala 1


def desenho(nome):
    def registrar(func):
        REGISTRO[nome] = func
        return func
    return registrar


def ancoras(nome, **params):
    f = ANCORAS.get(nome)
    return f(**params) if f else {}


@lru_cache(maxsize=2048)
def _obter(nome, escala, semente, progresso, params):
    return render(REGISTRO[nome](**dict(params)), escala=escala, semente=semente, progresso=progresso)


def obter(nome, escala=1.0, semente=0, progresso=1.0, **params):
    """Imagem RGBA + origem. Guarda em cache (a linha 'fervendo' so tem 3 desenhos por elemento)."""
    params = tuple(sorted((k, round(v, 3) if isinstance(v, float) else v) for k, v in params.items()))
    return _obter(nome, round(escala, 3), semente, round(progresso, 3), params)


# ---------- formas basicas ----------
def ret(x, y, w, h):
    return [(x, y), (x + w, y), (x + w, y + h), (x, y + h)]


def elipse(cx, cy, rx, ry, a0=0.0, a1=2 * math.pi, n=40):
    completo = abs(a1 - a0) >= 2 * math.pi - 1e-6
    return [(cx + rx * math.cos(a0 + (a1 - a0) * i / n), cy + ry * math.sin(a0 + (a1 - a0) * i / n))
            for i in range(n if completo else n + 1)]


def ret_arred(x, y, w, h, r, n=5):
    r = min(r, w / 2, h / 2)
    cantos = [(x + w - r, y + r, -math.pi / 2), (x + w - r, y + h - r, 0), (x + r, y + h - r, math.pi / 2), (x + r, y + r, math.pi)]
    pts = []
    for cx, cy, a in cantos:
        pts += [(cx + r * math.cos(a + math.pi / 2 * i / n), cy + r * math.sin(a + math.pi / 2 * i / n)) for i in range(n + 1)]
    return pts


def gira(pts, ang, cx=0.0, cy=0.0):
    c, s = math.cos(ang), math.sin(ang)
    return [(cx + (x - cx) * c - (y - cy) * s, cy + (x - cx) * s + (y - cy) * c) for x, y in pts]


def move(pts, dx, dy):
    return [(x + dx, y + dy) for x, y in pts]


def coracao_pts(cx, cy, largura, n=40):
    k = largura / 32
    pts = []
    for i in range(n):
        a = 2 * math.pi * i / n
        x = 16 * math.sin(a) ** 3
        y = -(13 * math.cos(a) - 5 * math.cos(2 * a) - 2 * math.cos(3 * a) - math.cos(4 * a))
        pts.append((cx + x * k, cy + (y + 2) * k))
    return pts


def gota_pts(cx, cy, r, ang=0.0):
    """Gota com a ponta para cima (ang gira a gota)."""
    pts = [(0, -1.9 * r)] + [(r * math.cos(a), r * math.sin(a)) for a in
                             [math.radians(d) for d in range(-30, 211, 15)]]
    return move(gira(pts, ang), cx, cy)


def onda_pts(x0, x1, y, amp, periodos, n=40):
    return [(x0 + (x1 - x0) * i / n, y + amp * math.sin(2 * math.pi * periodos * i / n)) for i in range(n + 1)]


def ponta(de, para, tam=26, **kw):
    a = math.atan2(para[1] - de[1], para[0] - de[0])
    return Traco([(para[0] - tam * math.cos(a - 0.5), para[1] - tam * math.sin(a - 0.5)), para,
                  (para[0] - tam * math.cos(a + 0.5), para[1] - tam * math.sin(a + 0.5))], **kw)


def bezier(p0, p1, p2, p3, n=30):
    out = []
    for i in range(n + 1):
        t = i / n
        u = 1 - t
        out.append((u ** 3 * p0[0] + 3 * u * u * t * p1[0] + 3 * u * t * t * p2[0] + t ** 3 * p3[0],
                    u ** 3 * p0[1] + 3 * u * u * t * p1[1] + 3 * u * t * t * p2[1] + t ** 3 * p3[1]))
    return out


def forma(pts, preench="objeto", esp=None, opacidade=1.0):
    """Preenchimento + contorno: o padrao de quase todo objeto."""
    return [Mancha(pts, preench, opacidade), Traco(pts, espessura=esp, fechado=True)]


def raios(cx, cy, r0, r1, n, a0=0.0, a1=2 * math.pi, **kw):
    out = []
    for i in range(n):
        a = a0 + (a1 - a0) * (i + 0.5) / n if a1 - a0 < 2 * math.pi - 1e-6 else a0 + 2 * math.pi * i / n
        out.append(Traco([(cx + r0 * math.cos(a), cy + r0 * math.sin(a)), (cx + r1 * math.cos(a), cy + r1 * math.sin(a))], **kw))
    return out


def rosto_assustado(cx, cy, k=1.0):
    c = []
    for sx in (-1, 1):
        c.append(Mancha(elipse(cx + sx * 36 * k, cy - 6 * k, 13 * k, 13 * k, n=16), "principal", deslocamento=(0, 0), tremor=0.4))
        c.append(Mancha(elipse(cx + sx * 36 * k + 4 * k, cy - 10 * k, 4 * k, 4 * k, n=10), "fundo", deslocamento=(0, 0), tremor=0))
        c.append(Traco([(cx + sx * 54 * k, cy - 30 * k), (cx + sx * 22 * k, cy - 44 * k)], espessura=6, halo=False))  # sobrancelha de medo
    c.append(Traco([(cx - 22 * k, cy + 40 * k), (cx - 11 * k, cy + 32 * k), (cx, cy + 40 * k), (cx + 11 * k, cy + 32 * k), (cx + 22 * k, cy + 40 * k)],
                   espessura=6, halo=False, tremor=1.0))
    return c


# =====================================================================
# Elementos
# =====================================================================
@desenho("cartao_papel")
def cartao_papel(largura=560, altura=150):
    x, y = -largura / 2, -altura / 2
    c = [Mancha(ret(x, y, largura, altura), "fundo", deslocamento=(0, 0))]
    for k in (1, 2):
        yy = y + altura * k / 3
        c.append(Traco([(x + 18, yy), (x + largura - 18, yy)], cor="pauta", espessura=2, halo=False, tremor=0.8, textura=False))
    c.append(Traco(ret(x, y, largura, altura), fechado=True, espessura=6))
    return Desenho(c)


@desenho("texto_mao")
def texto_mao(texto="texto", tamanho=64, papel="titulo", cor="principal", rotacao=0.0):
    return Desenho([Texto(texto, 0, 0, papel, tamanho, cor, "mm", rotacao)])


@desenho("contador")
def contador(texto="verdade #1", concluido=False, tamanho=56):
    """Origem na esquerda-meio do texto (fica no canto superior esquerdo)."""
    f = fonte("titulo", tamanho)
    num = texto.split("#")[-1]
    larg = f.getlength(texto)
    cx = larg - f.getlength(num) / 2
    c = [Texto(texto, 0, 0, "titulo", tamanho, "principal", "lm"),
         Traco(elipse(cx, 2, 26 + 12 * len(num), 36, a0=-2.4, a1=-2.4 + 2.25 * math.pi), espessura=5)]
    if concluido:
        c.append(Traco([(larg + 26, 0), (larg + 40, 18), (larg + 72, -26)], cor="apoio", espessura=9))
    return Desenho(c)


@desenho("cronometro")
def cronometro(ponteiro=0.0):
    r, cy = 58, 10
    c = [Traco(ret(-13, cy - r - 24, 26, 14), fechado=True, espessura=6),
         Traco([(0, cy - r - 10), (0, cy - r)], espessura=6),
         Traco([(r * 0.72, cy - r * 0.72), (r * 0.72 + 13, cy - r * 0.72 - 13)], espessura=7),
         *forma(elipse(0, cy, r, r)),
         Mancha(elipse(0, cy, r - 13, r - 13), "fundo")]
    for a in range(0, 360, 90):
        rad = math.radians(a)
        c.append(Traco([(math.sin(rad) * (r - 25), cy - math.cos(rad) * (r - 25)), (math.sin(rad) * (r - 17), cy - math.cos(rad) * (r - 17))],
                       espessura=4, halo=False, textura=False))
    c.append(Traco([(0, cy), (math.sin(ponteiro) * (r - 22), cy - math.cos(ponteiro) * (r - 22))], cor="apoio", espessura=7, halo=False))
    c.append(Mancha(elipse(0, cy, 6, 6, n=12), "principal", deslocamento=(0, 0), tremor=0))
    return Desenho(c)


@desenho("fita_metrica")
def fita_metrica(espiral=0.0):
    """Fita de costura: ondulada (espiral=0) ou enrolada em espiral hipnotica (espiral=1)."""
    n = 70
    centro = []
    for i in range(n + 1):
        s = i / n
        reta = (-125 + 250 * s, 20 * math.sin(2 * math.pi * 1.5 * s))
        th = s * 3.3 * math.pi + math.pi
        r = 16 + 96 * s
        esp = (r * math.cos(th), r * math.sin(th) * 0.95)
        centro.append((reta[0] + (esp[0] - reta[0]) * espiral, reta[1] + (esp[1] - reta[1]) * espiral))
    normais = []
    for i in range(n + 1):
        a, b = centro[max(0, i - 1)], centro[min(n, i + 1)]
        dx, dy = b[0] - a[0], b[1] - a[1]
        L = math.hypot(dx, dy) or 1
        normais.append((-dy / L, dx / L))
    meia = 13
    borda1 = [(x + nx * meia, y + ny * meia) for (x, y), (nx, ny) in zip(centro, normais)]
    borda2 = [(x - nx * meia, y - ny * meia) for (x, y), (nx, ny) in zip(centro, normais)]
    c = [Traco(centro, cor="destaque", espessura=2 * meia, halo=True, tremor=0.8, textura=False),
         Traco(borda1, espessura=4, halo=False, tremor=0.8),
         Traco(borda2, espessura=4, halo=False, tremor=0.8)]
    for i in range(3, n, 3):
        (x, y), (nx, ny) = centro[i], normais[i]
        tam = 9 if i % 9 == 0 else 5
        c.append(Traco([(x + nx * meia, y + ny * meia), (x + nx * (meia - tam), y + ny * (meia - tam))], espessura=3, halo=False, textura=False, tremor=0.3))
    (x, y), (nx, ny) = centro[-1], normais[-1]
    c.append(Traco([(x + nx * (meia + 2), y + ny * (meia + 2)), (x - nx * (meia + 2), y - ny * (meia + 2))], espessura=10, halo=False))
    return Desenho(c)


@desenho("gotas_suor")
def gotas_suor(n=3):
    lugares = [(0, 0, 0.0, 16), (46, -34, 0.35, 13), (-40, -46, -0.3, 11), (70, 20, 0.5, 11), (-24, 44, -0.2, 10), (24, 60, 0.15, 12)]
    c = []
    for cx, cy, ang, r in lugares[:max(1, min(n, len(lugares)))]:
        c += forma(gota_pts(cx, cy, r, ang), "fundo", esp=6)
        c.append(Traco([(cx - r * 0.35, cy - r * 0.1), (cx - r * 0.3, cy + r * 0.35)], cor="destaque", espessura=4, halo=False, textura=False))
    return Desenho(c)


@desenho("espelho")
def espelho(espremer=0.0):
    k = 1 - 0.5 * espremer
    c = forma(ret_arred(-14, 40, 28, 96, 12)) + forma(elipse(0, -40, 74, 94))
    c += forma(elipse(0, -40, 58 * k, 78), "fundo", esp=5)
    c += [Traco([(-30 * k, -86), (-12 * k, -104)], cor="destaque", espessura=6, halo=False, textura=False),
          Traco([(-38 * k, -66), (-30 * k, -74)], cor="destaque", espessura=6, halo=False, textura=False)]
    for sx in (-1, 1):  # reflexo: carinha espremida
        c.append(Mancha(elipse(sx * 18 * k, -48, 6 * k + 1, 7, n=12), "principal", deslocamento=(0, 0), tremor=0.3))
    c.append(Traco([(-14 * k, -14), (0, -8), (14 * k, -14)], espessura=5, halo=False))
    if espremer > 0.15:
        for sx in (-1, 1):
            x = sx * (96 + 10 * espremer)
            c.append(Traco([(x + sx * 26, -60), (x, -40), (x + sx * 26, -20)], cor="apoio", espessura=7))
    return Desenho(c)


@desenho("seta_subindo")
def seta_subindo():
    pts = [(-100, 95), (-45, 35), (-12, 62), (60, -30)]
    return Desenho([Traco(pts, espessura=10), ponta(pts[-2], pts[-1], 34, espessura=10)])


@desenho("seta")
def seta(origem=(-100, 60), destino=(100, -60), curva=0.35):
    (x0, y0), (x1, y1) = origem, destino
    dx, dy = x1 - x0, y1 - y0
    nx, ny = -dy * curva, dx * curva
    pts = bezier((x0, y0), (x0 + dx * 0.3 + nx, y0 + dy * 0.3 + ny), (x0 + dx * 0.7 + nx, y0 + dy * 0.7 + ny), (x1, y1))
    return Desenho([Traco(pts, espessura=8), ponta(pts[-4], pts[-1], 30, espessura=8)])


@desenho("celular")
def celular(rec=True):
    c = forma(ret_arred(-74, -130, 148, 260, 24), "fundo") + [
        Traco(ret_arred(-58, -102, 116, 198, 8), fechado=True, espessura=4, halo=False),
        Traco([(-16, -116), (16, -116)], espessura=5, halo=False),
        Traco([(-12, 114), (12, 114)], espessura=5, halo=False)]
    if rec:
        c += [Mancha(elipse(-38, -86, 6, 6, n=12), "apoio", deslocamento=(0, 0), tremor=0.3),
              Texto("REC", -26, -86, "anotacao", 18, "apoio", "lm", halo=False)]
    return Desenho(c)


@desenho("prato_salada")
def prato_salada():
    c = []
    folhas = [(-40, -24, -0.6), (-6, -40, -0.1), (30, -28, 0.5), (12, -18, 0.2)]
    for cx, cy, ang in folhas:
        pts = move(gira([(-30, 0), (-14, -14), (14, -14), (30, 0), (14, 12), (-14, 12)], ang), cx, cy)
        c += forma(pts, "fundo", esp=5)
        c.append(Traco(move(gira([(-22, 0), (22, 0)], ang), cx, cy), espessura=3, halo=False, textura=False))
    for cx, cy in ((-20, -12), (44, -12)):
        c += forma(elipse(cx, cy, 13, 13, n=16), "apoio", esp=5)
    c += forma(elipse(0, 0, 84, 50, a0=0, a1=math.pi) + [(-84, 0)], "objeto")
    c += forma(elipse(0, 0, 84, 14), "fundo", esp=6)
    return Desenho(c)


@desenho("coracao")
def coracao(largura=110):
    return Desenho(forma(coracao_pts(0, 0, largura), "apoio") +
                   [Traco(elipse(-largura * 0.25, -largura * 0.18, largura * 0.12, largura * 0.12, a0=3.4, a1=4.6, n=8),
                          cor="fundo", espessura=5, halo=False, textura=False)])


@desenho("coracoes")
def coracoes():
    c = []
    for cx, cy, L in ((-40, 30, 70), (30, -10, 52), (-6, -70, 38)):
        c += forma(coracao_pts(cx, cy, L), "apoio", esp=6)
    return Desenho(c)


@desenho("wifi")
def wifi():
    c = [Mancha(elipse(0, 70, 13, 13, n=16), "principal", deslocamento=(0, 0), tremor=0.4)]
    for r in (50, 95, 140):
        c.append(Traco(elipse(0, 70, r, r, a0=math.radians(-138), a1=math.radians(-42), n=24), espessura=13))
    return Desenho(c)


@desenho("megafone")
def megafone(ondas=0.0):
    c = forma([(-30, 18), (-24, 62), (-6, 62), (-8, 18)])
    c += forma([(-100, -22), (-34, -22), (62, -74), (62, 74), (-34, 22), (-100, 22)])
    c += forma(elipse(62, 0, 14, 74), "fundo", esp=7)
    if ondas > 0:
        for k, r in enumerate((40, 70, 100)):
            rr = r * (0.6 + 0.4 * ondas)
            c.append(Traco(elipse(62, 0, rr, rr * 1.1, a0=-0.7, a1=0.7, n=14), espessura=8))
    return Desenho(c)


@desenho("balanca")
def balanca(inclinacao=0.0, rotulo="magreza", coracao=False):
    """inclinacao em radianos: negativa = lado esquerdo desce."""
    eixo = (0, -80)
    braco = gira([(-120, -80), (120, -80)], inclinacao, *eixo)
    c = forma([(-60, 150), (60, 150), (34, 124), (-34, 124)])
    c.append(Traco([(0, 126), (0, -74)], espessura=10))
    for (ex, ey), lado in zip(braco, (-1, 1)):
        prato = (ex, ey + 100)
        c += [Traco([(ex, ey), (prato[0] - 46, prato[1])], espessura=4, halo=True, textura=False),
              Traco([(ex, ey), (prato[0] + 46, prato[1])], espessura=4, halo=True, textura=False)]
        if lado == 1 and coracao:
            c += forma(coracao_pts(prato[0], prato[1] - 26, 58), "apoio", esp=6)
        c += forma(elipse(prato[0], prato[1], 54, 26, a0=0, a1=math.pi) + [(prato[0] - 54, prato[1])])
        if lado == -1 and rotulo:
            c.append(Texto(rotulo, prato[0], prato[1] + 58, "titulo", 52, "principal", "mm"))
    c.append(Traco(braco, espessura=10))
    c += forma(elipse(*eixo, 11, 11, n=14), "destaque", esp=6)
    return Desenho(c)


@desenho("borrifador")
def borrifador(borrifo=0.0):
    c = forma(ret_arred(-56, -22, 112, 152, 20))
    c += forma(ret(-40, 26, 80, 56), "fundo", esp=5)
    c.append(Traco(onda_pts(-28, 28, 54, 6, 1.5, 16), cor="apoio", espessura=5, halo=False))
    c += forma([(-30, -22), (-22, -52), (22, -52), (30, -22)])
    c += forma([(-38, -52), (-38, -92), (40, -92), (64, -80), (40, -68), (28, -52)], "fundo")
    c.append(Traco([(-6, -52), (-22, -20), (-4, -26)], espessura=7))
    if borrifo > 0:
        for i, (dx, dy, r) in enumerate([(30, -6, 5), (52, -24, 7), (60, 10, 5), (80, -10, 9), (96, -34, 6), (104, 14, 7), (124, -14, 11)]):
            if i / 7 < borrifo:
                cx, cy = 64 + dx * borrifo, -80 + dy * borrifo
                c.append(Traco(elipse(cx, cy, r, r, n=12), fechado=True, espessura=4, halo=True))
    return Desenho(c)


@desenho("pao")
def pao(tipo="forma", boina=False, suor=0):
    c = []
    if tipo == "frances":
        corpo = gira(elipse(0, 0, 130, 62), -0.12)
        c += forma(corpo)
        for x in (-55, 0, 55):
            c.append(Traco(gira([(x - 20, -26), (x, -40), (x + 20, -46)], -0.12), espessura=6, halo=False))
        c += rosto_assustado(0, 14, 0.8)
        topo = (8, -62)
    else:
        pts = [(-95, 85), (-95, -24)] + elipse(0, -40, 112, 72, a0=math.pi, a1=2 * math.pi, n=24)[1:-1] + [(95, -24), (95, 85)]
        c += forma(pts)
        c += rosto_assustado(0, 0)
        topo = (30, -112)
    for i, (dx, dy) in enumerate([(-150, -50), (140, -70), (-160, 20)][:suor]):
        c += forma(gota_pts(dx, dy, 13, 0.3 if dx > 0 else -0.3), "fundo", esp=6)
    if boina:
        bx, by = topo
        c.append(Traco([(bx + 4, by - 18), (bx + 10, by - 36)], espessura=9))
        c += forma(move(gira(elipse(0, 0, 74, 24), -0.22), bx, by), "principal")
    return Desenho(c)


@desenho("ring_light")
def ring_light(brilho=0.0):
    c = [Traco([(0, 100), (0, 205)], espessura=9),
         Traco([(0, 200), (-54, 262)], espessura=8), Traco([(0, 200), (54, 262)], espessura=8), Traco([(0, 200), (0, 264)], espessura=8),
         Traco(elipse(0, 0, 84, 84), cor="destaque", espessura=26, fechado=True, textura=False),
         Traco(elipse(0, 0, 98, 98), fechado=True, espessura=6),
         Traco(elipse(0, 0, 70, 70), fechado=True, espessura=6, halo=False)]
    c += forma(ret_arred(-24, -42, 48, 84, 9), "fundo", esp=6)
    if brilho > 0:
        c += raios(0, 0, 112, 112 + 26 * brilho, 10, cor="principal", espessura=6)
    return Desenho(c)


@desenho("etiqueta_preco")
def etiqueta_preco(texto="R$", tamanho=44):
    larg = max(80, fonte("titulo", tamanho).getlength(texto) + 44)
    x0 = -larg / 2 - 16
    pts = [(x0, -38), (x0 + larg, -38), (x0 + larg + 36, 0), (x0 + larg, 38), (x0, 38)]
    furo = (x0 + larg + 12, 0)
    return Desenho([Traco([furo, (furo[0] + 30, -40), (furo[0] + 18, -84)], espessura=4, textura=False),
                    *forma(pts, "fundo"),
                    Traco(elipse(*furo, 8, 8, n=12), fechado=True, espessura=4, halo=False),
                    Texto(texto, x0 + larg / 2, 2, "titulo", tamanho, "principal", "mm", halo=False)])


@desenho("lista_tarefas")
def lista_tarefas(comprimento=1.0):
    L = 180 * comprimento
    c = forma(ret(-80, -100, 160, L + 10), "fundo")
    y = -76
    while y < -100 + L - 20:
        c.append(Traco(ret(-62, y - 9, 18, 18), fechado=True, espessura=4, halo=False))
        c.append(Traco(onda_pts(-32, 58, y, 3, 2.5, 14), espessura=4, halo=False, textura=False))
        y += 40
    c += forma(elipse(0, -100 + L + 12, 84, 12), "objeto", esp=6)
    c += forma(ret_arred(-96, -132, 192, 34, 16))
    return Desenho(c)


@desenho("tenis")
def tenis():
    c = forma([(-104, 28), (98, 28), (106, 46), (-104, 50)], "fundo")
    c += forma([(-98, 30), (-96, -8), (-66, -42), (-22, -38), (8, -12), (62, -2), (98, 14), (98, 30)])
    c += [Traco([(-60, -30), (-36, -12)], espessura=4, halo=False), Traco([(-46, -36), (-24, -18)], espessura=4, halo=False),
          Traco([(-34, -40), (-14, -24)], espessura=4, halo=False),
          Traco(onda_pts(-80, 80, 12, 5, 1.2, 16), cor="apoio", espessura=6, halo=False)]
    return Desenho(c)


@desenho("halter")
def halter():
    c = [Traco([(-92, 0), (92, 0)], espessura=14)]
    for sx in (-1, 1):
        c += forma(ret_arred(sx * 58 - 12, -48, 24, 96, 8))
        c += forma(ret_arred(sx * 86 - 10, -36, 20, 72, 7), "destaque")
    c += [Traco([(-20, -10), (-20, 10)], espessura=3, halo=False), Traco([(0, -10), (0, 10)], espessura=3, halo=False),
          Traco([(20, -10), (20, 10)], espessura=3, halo=False)]
    return Desenho(c)


@desenho("tapete_yoga")
def tapete_yoga():
    c = forma(ret(-84, -38, 160, 76), "destaque")
    c += [Traco([(-40, -38), (-40, 38)], cor="apoio", espessura=8, halo=False), Traco([(30, -38), (30, 38)], cor="apoio", espessura=8, halo=False)]
    c += forma(elipse(-84, 0, 22, 38), "objeto")
    espiral = [(-84 + 3 * t * math.cos(t) * 0.55, 3 * t * math.sin(t)) for t in [i * 0.3 for i in range(38)]]
    c.append(Traco(espiral, espessura=4, halo=False, tremor=0.5))
    return Desenho(c)


@desenho("balao_pensamento")
def balao_pensamento(texto="?"):
    pts = []
    for i in range(72):
        a = 2 * math.pi * i / 72
        r = 1 + 0.09 * abs(math.sin(4.5 * a))
        pts.append((120 * r * math.cos(a), 72 * r * math.sin(a)))
    c = forma(elipse(-98, 96, 10, 10, n=12), "fundo", esp=5) + forma(elipse(-76, 72, 17, 17, n=16), "fundo", esp=6)
    c += forma(pts, "fundo")
    if texto:
        c.append(Texto(texto, 0, 0, "titulo", 76, "apoio", "mm", halo=False))
    return Desenho(c)


@desenho("relogio_ponto")
def relogio_ponto(texto="9h–18h"):
    c = forma(elipse(0, -20, 64, 64), "fundo")
    for h in range(12):
        a = 2 * math.pi * h / 12
        r0 = 50 if h % 3 else 44
        c.append(Traco([(math.sin(a) * r0, -20 - math.cos(a) * r0), (math.sin(a) * 56, -20 - math.cos(a) * 56)], espessura=4, halo=False, textura=False))
    c += [Traco([(0, -20), (-36, -20)], espessura=8, halo=False), Traco([(0, -20), (0, -66)], cor="apoio", espessura=6, halo=False)]
    c.append(Texto(texto, 0, 82, "titulo", 42, "principal", "mm"))
    return Desenho(c)


@desenho("cracha")
def cracha(texto="CLT"):
    c = [Traco([(-14, -118), (-34, -214)], cor="apoio", espessura=8), Traco([(14, -118), (34, -214)], cor="apoio", espessura=8)]
    c += forma(ret_arred(-22, -126, 44, 26, 6))
    c += forma(ret_arred(-80, -104, 160, 214, 18), "fundo")
    c += forma(ret(-56, -78, 56, 64), "objeto", esp=5)
    c += [Traco(elipse(-28, -54, 12, 12, n=14), fechado=True, espessura=4, halo=False),
          Traco(elipse(-28, -20, 22, 14, a0=math.pi, a1=2 * math.pi, n=12), espessura=4, halo=False),
          Traco([(14, -64), (56, -64)], espessura=5, halo=False), Traco([(14, -40), (46, -40)], espessura=5, halo=False),
          Texto(texto, 0, 38, "titulo", 60, "apoio", "mm", halo=False),
          Traco([(-50, 84), (50, 84)], espessura=4, halo=False)]
    return Desenho(c)


@desenho("sol")
def sol():
    return Desenho(raios(0, 0, 66, 92, 10, espessura=8) + forma(elipse(0, 0, 52, 52), "destaque"))


@desenho("ondas")
def ondas():
    c = [Mancha(onda_pts(-140, 140, -10, 12, 2) + [(140, 46), (-140, 46)], "objeto", deslocamento=(0, 0))]
    for k, y in enumerate((-10, 20, 46)):
        c.append(Traco(onda_pts(-140 + k * 10, 140 - k * 10, y, 12, 2), espessura=8 if k == 0 else 6, halo=k == 0))
    return Desenho(c)


@desenho("guarda_sol")
def guarda_sol():
    topo = (0, -96)
    vieiras = []
    for i in range(4):
        vieiras += elipse(-96 + 64 * i, 0, 32, 16, a0=math.pi, a1=0, n=10)
    copa = elipse(0, 0, 128, 96, a0=math.pi, a1=2 * math.pi, n=24) + [(128, 0)] + vieiras[::-1]
    c = [Traco([(4, -96), (18, 176)], espessura=9)]
    c += forma(elipse(20, 178, 70, 20, a0=math.pi, a1=2 * math.pi, n=14) + [(90, 178)], "objeto")
    c.append(Mancha(copa, "fundo"))
    for i in (0, 2):
        c.append(Mancha([topo, (-128 + 64 * i, 0), (-64 + 64 * i, 0)], "apoio"))
    for i in range(1, 4):
        c.append(Traco([topo, (-128 + 64 * i, 0)], espessura=5, halo=False))
    c.append(Traco(copa, fechado=True))
    c += forma(elipse(*topo, 9, 9, n=12), "destaque", esp=5)
    return Desenho(c)


@desenho("binoculos")
def binoculos():
    c = []
    for sx in (-1, 1):
        c += forma(ret_arred(sx * 52 - 30, -70, 60, 84, 16))
        c += forma(ret_arred(sx * 52 - 20, -96, 40, 30, 8))
    c += forma(ret(-16, -50, 32, 30))
    for sx in (-1, 1):
        c += forma(elipse(sx * 52, 26, 44, 44), "fundo", esp=9)
        c += forma(elipse(sx * 52, 26, 26, 26), "objeto", esp=5)
        c.append(Traco(elipse(sx * 52 - 10, 16, 12, 12, a0=3.4, a1=4.6, n=8), cor="fundo", espessura=5, halo=False, textura=False))
    return Desenho(c)


@desenho("transferidor")
def transferidor(angulo=45, texto="45°"):
    cy, r = 50, 118
    c = [Mancha(elipse(0, cy, r, r, a0=math.pi, a1=2 * math.pi, n=30) + [(r, cy)], "fundo", opacidade=0.85),
         Traco(elipse(0, cy, r, r, a0=math.pi, a1=2 * math.pi, n=30) + [(r, cy), (-r, cy)], fechado=True, espessura=7),
         Traco(elipse(0, cy, r - 36, r - 36, a0=math.pi, a1=2 * math.pi, n=24), espessura=3, halo=False, textura=False)]
    for g in range(0, 181, 15):
        a = math.radians(180 + g)
        r0 = r - (18 if g % 45 == 0 else 10)
        c.append(Traco([(r0 * math.cos(a), cy + r0 * math.sin(a)), ((r - 4) * math.cos(a), cy + (r - 4) * math.sin(a))], espessura=3, halo=False, textura=False))
    a = math.radians(-angulo)
    c += [Traco([(0, cy), (math.cos(a) * (r + 30), cy + math.sin(a) * (r + 30))], cor="apoio", espessura=8),
          Traco([(0, cy), (r + 30, cy)], cor="apoio", espessura=8),
          Traco(elipse(0, cy, 46, 46, a0=a, a1=0, n=10), cor="apoio", espessura=6, halo=False),
          Mancha(elipse(0, cy, 7, 7, n=12), "principal", deslocamento=(0, 0), tremor=0)]
    if texto:
        c.append(Texto(texto, -52, cy - 38, "titulo", 44, "principal", "mm", halo=False))
    return Desenho(c)


@desenho("lupa")
def lupa():
    return Desenho([Traco([(26, 26), (92, 92)], espessura=24), Traco([(78, 78), (96, 96)], cor="destaque", espessura=14, halo=False),
                    Mancha(elipse(-20, -20, 58, 58), "fundo", opacidade=0.55, deslocamento=(0, 0)),
                    Traco(elipse(-20, -20, 58, 58), fechado=True, espessura=14),
                    Traco(elipse(-30, -30, 34, 34, a0=3.3, a1=4.5, n=10), cor="fundo", espessura=7, halo=False, textura=False)])


@desenho("biceps")
def biceps(brilho=0.0):
    braco = [(-112, 72), (-20, 76), (42, 72), (82, 56), (98, 26), (100, -12), (92, -52), (74, -78),
             (46, -76), (40, -40), (36, -10), (18, -16), (0, -44), (-30, -56), (-62, -44), (-84, -22), (-112, -12)]
    c = forma(braco)
    c += forma(elipse(64, -96, 32, 30), "objeto")
    c += [Traco([(48, -112), (60, -100)], espessura=4, halo=False), Traco([(42, -96), (56, -86)], espessura=4, halo=False),
          Traco([(-46, -14), (-26, 2), (-2, -4)], espessura=5, halo=False)]
    if brilho > 0:
        for a, r in ((-2.2, 1.0), (-1.7, 1.15), (-1.2, 1.0)):
            r0, r1 = 74 * r, (74 + 34 * brilho) * r
            c.append(Traco([(-34 + r0 * math.cos(a), -40 + r0 * math.sin(a)), (-34 + r1 * math.cos(a), -40 + r1 * math.sin(a))], cor="apoio", espessura=7))
    return Desenho(c)


@desenho("fabrica")
def fabrica(fumaca=0.0):
    telhado = [(-112, 100), (-112, 0)]
    for i in range(3):
        x = -112 + 56 * i
        telhado += [(x, -42), (x + 56, 0)]
    telhado += [(112, 0), (112, 100)]
    c = forma(ret(56, -116, 32, 120))
    c += forma(telhado)
    for x in (-88, -40, 8):
        c += forma(ret(x, 22, 30, 28), "destaque", esp=5)
    c += forma(ret(54, 44, 36, 56), "fundo", esp=5)
    if fumaca > 0:
        for i, (dx, dy, r) in enumerate([(0, -18, 14), (18, -50, 20), (44, -86, 26)]):
            if i / 3 < fumaca:
                c += forma(elipse(72 + dx, -126 + dy, r, r * 0.85, n=16), "fundo", esp=5)
    return Desenho(c)


@desenho("lampada")
def lampada(acesa=0.0):
    bulbo = elipse(0, -26, 52, 52, a0=math.radians(125), a1=math.radians(415), n=30) + [(24, 30), (-24, 30)]
    c = []
    if acesa > 0:
        c += raios(0, -26, 70, 70 + 30 * acesa, 9, a0=math.radians(-200), a1=math.radians(20), cor="apoio", espessura=7)
    c += forma(bulbo, "destaque" if acesa >= 0.5 else "fundo")
    filamento = [(-12, 30), (-12, -6)] + elipse(0, -14, 12, 9, a0=math.pi, a1=3 * math.pi, n=16) + [(12, -6), (12, 30)]
    c += [Traco(filamento, espessura=4, halo=False, tremor=0.6),
          *forma(ret_arred(-26, 30, 52, 14, 5), "objeto", esp=5), *forma(ret_arred(-22, 44, 44, 14, 5), "objeto", esp=5),
          Traco([(-10, 62), (10, 62)], espessura=6, halo=False)]
    return Desenho(c)


@desenho("selo")
def selo(texto="+PROTEÍNA"):
    pts = []
    for i in range(96):
        a = 2 * math.pi * i / 96
        r = 1 + 0.04 * math.cos(24 * a)
        pts.append((168 * r * math.cos(a), 74 * r * math.sin(a)))
    tam = 54
    while tam > 18 and fonte("titulo", tam).getlength(texto) > 286:
        tam -= 2
    return Desenho(forma(pts, "apoio") + [Traco(elipse(0, 0, 156, 62), fechado=True, cor="fundo", espessura=3, halo=False, textura=False),
                                          Texto(texto, 0, 2, "titulo", tam, "fundo", "mm", halo=False)])


@desenho("cifroes")
def cifroes():
    return Desenho([Texto("$", -54, 24, "titulo", 84, "principal", "mm", -12), Texto("$", 6, -34, "titulo", 104, "apoio", "mm", 6),
                    Texto("$", 62, 18, "titulo", 76, "principal", "mm", 16)])


@desenho("sacola")
def sacola():
    c = [Traco(elipse(-30, -42, 22, 54, a0=math.pi, a1=2 * math.pi, n=14), espessura=8),
         Traco(elipse(30, -42, 22, 54, a0=math.pi, a1=2 * math.pi, n=14), espessura=8)]
    c += forma([(-84, -42), (84, -42), (96, 112), (-96, 112)])
    c += [Traco([(-84, -18), (86, -18)], espessura=4, halo=False), *forma(coracao_pts(0, 40, 50), "apoio", esp=5)]
    return Desenho(c)


@desenho("garrafa_agua")
def garrafa_agua():
    c = forma(ret_arred(-24, -158, 48, 28, 6), "apoio")
    c += forma([(-20, -130), (20, -130), (46, -86), (-46, -86)], "fundo")
    c += [Mancha(ret_arred(-50, -86, 100, 228, 20), "fundo", deslocamento=(0, 0)),
          Mancha(onda_pts(-46, 46, -40, 6, 1.5, 16) + [(46, 136), (-46, 136)], "pauta", deslocamento=(0, 0)),
          Traco(onda_pts(-46, 46, -40, 6, 1.5, 16), espessura=4, halo=False),
          Traco(ret_arred(-50, -86, 100, 228, 20), fechado=True)]
    c += forma(ret(-50, 8, 100, 52), "destaque", esp=6)
    return Desenho(c)


@desenho("item_lista")
def item_lista(texto="item", numero=None, marcado=False, tamanho=46):
    """Linha de lista: caixinha (ou numero numa bolinha) + texto. Origem na esquerda-meio."""
    c = []
    if numero is not None:
        c += forma(elipse(26, 0, 27, 27, n=20), "destaque", esp=6)
        c.append(Texto(str(numero), 26, 2, "titulo", 36, "principal", "mm", halo=False))
    else:
        c += forma(ret(4, -22, 44, 44), "fundo", esp=6)
        if marcado:
            c.append(Traco([(8, 0), (22, 18), (54, -30)], cor="apoio", espessura=10))
    c.append(Texto(texto, 72, 2, "legenda", tamanho, "texto", "lm"))
    return Desenho(c)


# ---------- pontos de encaixe ----------
def _ancoras_balanca(inclinacao=0.0, **_):
    esq, dir_ = gira([(-120, -80), (120, -80)], inclinacao, 0, -80)
    return {"prato_esq": (esq[0], esq[1] + 74), "prato_dir": (dir_[0], dir_[1] + 74), "dentro": (dir_[0], dir_[1] + 74)}


ANCORAS.update({
    "balanca": _ancoras_balanca,
    "celular": lambda **_: {"dentro": (0, -4), "acima": (0, -170)},
    "fabrica": lambda **_: {"chamine": (90, -190), "acima": (-40, -110)},
    "ring_light": lambda **_: {"suporte": (64, 160)},
    "garrafa_agua": lambda **_: {"rotulo": (0, 34)},
    "halter": lambda **_: {"acima": (0, -95)},
})


# ---------- extras genericos da biblioteca ----------
@desenho("linha")
def linha(pontos=((-100, 0), (100, 0)), espessura=9, cor="principal"):
    return Desenho([Traco([tuple(p) for p in pontos], cor=cor, espessura=espessura)])


@desenho("circulo")
def circulo(rx=120, ry=100, voltas=1.12):
    return Desenho([Traco(elipse(0, 0, rx, ry, a0=-2.6, a1=-2.6 + voltas * 2 * math.pi, n=round(48 * voltas)), espessura=9, tremor=4)])


@desenho("check")
def check():
    return Desenho([Traco([(-40, 0), (-12, 30), (44, -40)], cor="apoio", espessura=12)])


@desenho("xis")
def xis():
    return Desenho([Traco([(-40, -40), (40, 40)], cor="apoio", espessura=12), Traco([(40, -40), (-40, 40)], cor="apoio", espessura=12)])


@desenho("casa")
def casa():
    c = forma([(-90, -10), (0, -96), (90, -10)], "apoio")
    c += forma(ret(-72, -14, 144, 110), "fundo")
    c += forma(ret(-20, 36, 40, 60), "objeto", esp=6) + forma(ret(30, 6, 30, 28), "destaque", esp=5)
    return Desenho(c)


@desenho("grafico")
def grafico():
    c = [Traco([(-100, -100), (-100, 96), (104, 96)], espessura=8)]
    for i, h in enumerate((60, 100, 80, 150)):
        c += forma(ret(-78 + 46 * i, 92 - h, 30, h), "destaque" if i == 3 else "objeto", esp=6)
    seta_pts = [(-84, 40), (-36, 0), (10, 20), (88, -86)]
    return Desenho(c + [Traco(seta_pts, cor="apoio", espessura=8), ponta(seta_pts[-2], seta_pts[-1], 28, cor="apoio", espessura=8)])


@desenho("balao_fala")
def balao_fala(texto=""):
    pts = ret_arred(-120, -70, 240, 120, 30)
    c = forma([(-60, 40), (-90, 96), (-20, 44)], "fundo") + forma(pts, "fundo")
    if texto:
        c.append(Texto(texto, 0, -10, "titulo", 44, "principal", "mm", halo=False))
    else:
        c += [Traco(onda_pts(-80, 80, -26, 4, 2, 16), espessura=5, halo=False), Traco(onda_pts(-80, 40, 6, 4, 1.5, 12), espessura=5, halo=False)]
    return Desenho(c)


@desenho("dinheiro")
def dinheiro():
    c = forma(gira(ret_arred(-110, -56, 220, 112, 10), -0.08), "objeto")
    c += [Traco(gira(elipse(0, 0, 34, 34), -0.08), fechado=True, espessura=5, halo=False),
          Texto("$", 0, 2, "titulo", 52, "principal", "mm", halo=False)]
    return Desenho(c)


# =====================================================================
# Video 2 (verdades-shape-slim): objetos e a piada do "esquecido" (teia de aranha + cara triste)
# =====================================================================
def teia(cx, cy, r=70, lado=1):
    """Teia presa no canto (cx, cy), abrindo para baixo e para dentro (lado=1: canto direito), com aranha pendurada."""
    c = []
    angs = [math.pi / 2 + lado * (math.pi / 2) * i / 4 for i in range(5)]  # de "para baixo" ate "para dentro"
    raio = lambda a, k: (cx + r * k * math.cos(a), cy + r * k * math.sin(a))
    for a in angs:
        c.append(Traco([(cx, cy), raio(a, 1)], espessura=3, halo=False, tremor=0.6, textura=False))
    for k in (0.35, 0.65, 0.95):
        pts = [raio(a, k) for a in angs]
        fio = []
        for p, q in zip(pts, pts[1:]):  # fios que cedem um pouco entre os raios
            m = ((p[0] + q[0]) / 2, (p[1] + q[1]) / 2)
            fio += [p, (m[0] + (cx - m[0]) * 0.12, m[1] + (cy - m[1]) * 0.12)]
        c.append(Traco(fio + [pts[-1]], espessura=3, halo=False, tremor=0.6, textura=False))
    ax, ay = cx - lado * r * 0.5, cy + r * 1.25
    c.append(Traco([(ax, cy + r * 0.55), (ax, ay - 9)], espessura=2, halo=False, textura=False))
    c.append(Mancha(elipse(ax, ay, 9, 9, n=12), "principal", deslocamento=(0, 0), tremor=0.3))
    for sx in (-1, 1):
        for dy in (-4, 3):
            c.append(Traco([(ax + sx * 7, ay + dy), (ax + sx * 16, ay + dy - 6), (ax + sx * 20, ay + dy + 4)], espessura=2.5, halo=False, textura=False))
    return c


def cara_triste(cx, cy, k=1.0):
    c = []
    for sx in (-1, 1):
        c.append(Mancha(elipse(cx + sx * 22 * k, cy, 6 * k, 7 * k, n=12), "principal", deslocamento=(0, 0), tremor=0.3))
        c.append(Traco([(cx + sx * 32 * k, cy - 14 * k), (cx + sx * 12 * k, cy - 20 * k)], espessura=4, halo=False))
    c.append(Traco(elipse(cx, cy + 34 * k, 16 * k, 10 * k, a0=math.pi * 1.1, a1=math.pi * 1.9, n=10), espessura=5, halo=False))
    c += forma(gota_pts(cx + 30 * k, cy + 18 * k, 6 * k, 0), "fundo", esp=3)  # lagrima
    return c


@desenho("poltrona")
def poltrona():
    c = forma([(-110, -60), (-100, -130), (100, -130), (110, -60), (110, 40), (-110, 40)])  # encosto
    c += forma(ret_arred(-150, -40, 54, 120, 22), "destaque") + forma(ret_arred(96, -40, 54, 120, 22), "destaque")  # bracos
    c += forma(ret_arred(-100, 10, 200, 60, 14), "fundo")  # assento
    c += [Traco([(-120, 80), (-126, 120)], espessura=9), Traco([(120, 80), (126, 120)], espessura=9),
          Traco([(-140, 80), (140, 80)], espessura=8)]
    c += [Traco(onda_pts(-80, 80, -90, 5, 2, 16), espessura=4, halo=False)]
    return Desenho(c)


@desenho("xicara")
def xicara(vapor=1.0):
    c = forma([(-56, -30), (56, -30), (44, 40), (-44, 40)], "fundo")
    c += [Traco(elipse(66, 0, 22, 20, a0=-1.4, a1=1.6, n=14), espessura=8)]
    c += forma(elipse(0, 50, 86, 14, n=24), "destaque", esp=6)
    c += [Traco(onda_pts(-50, 50, -6, 4, 1.5, 12), cor="apoio", espessura=5, halo=False)]
    for i, x in enumerate((-26, 4, 32)):
        h = 70 * vapor
        if h > 4:
            c.append(Traco([(x + 8 * math.sin(k * 1.4 + i), -44 - h * k / 6) for k in range(7)], espessura=5, tremor=1.5))
    return Desenho(c)


@desenho("riscos")
def riscos(n=20, texto="200x"):
    """Risquinhos de contagem (grupos de 5) com o total escrito em cima."""
    c = [Texto(texto, 0, -86, "titulo", 70, "principal", "mm")]
    for i in range(n):
        g, k = divmod(i, 5)
        gx, gy = -150 + (g % 4) * 84, -10 + (g // 4) * 96
        if k < 4:
            x = gx + k * 16
            c.append(Traco([(x, gy), (x + 3, gy + 70)], espessura=7))
        else:
            c.append(Traco([(gx - 12, gy + 52), (gx + 62, gy + 14)], cor="apoio", espessura=7))
    return Desenho(c)


@desenho("prato")
def prato(teia_=False):
    c = forma(elipse(0, 0, 120, 70, n=36), "fundo") + [Traco(elipse(0, 0, 86, 48, n=30), fechado=True, espessura=4, halo=False)]
    for dx, dy, a in ((-30, -8, 0.4), (14, -18, -0.5), (30, 12, 0.9), (-6, 16, -1.2)):
        c += forma(move(gira(elipse(0, 0, 26, 13, n=14), a), dx, dy), "objeto", esp=4)
    c += [Traco([(-150, -40), (-150, 60)], espessura=6), Traco([(-160, -40), (-160, -14), (-140, -14), (-140, -40)], espessura=4, halo=False)]
    c += forma([(150, -44), (162, -30), (158, 60), (148, 60)], "fundo", esp=5)
    if teia_:
        c += teia(118, -60, 80, 1) + cara_triste(0, -6, 0.9)
    return Desenho(c)


DIAS = "STQQSSD"


@desenho("calendario")
def calendario(dias=0, marca="check", fds=False):
    """Uma semana, de segunda a domingo: 'dias' marcados com check (ou cubinho de acucar riscado); 'fds' pinta o fim de semana."""
    w, h, x0, y0 = 340, 210, -170, -105
    c = forma(ret(x0, y0, w, h), "fundo") + forma(ret(x0, y0, w, 50), "destaque", esp=6)
    c += [Traco([(x0 + 60, y0 - 16), (x0 + 60, y0 + 16)], espessura=8), Traco([(x0 + w - 60, y0 - 16), (x0 + w - 60, y0 + 16)], espessura=8)]
    cel = w / 7
    for i, d in enumerate(DIAS):
        cx = x0 + cel * (i + 0.5)
        if i:
            c.append(Traco([(x0 + cel * i, y0 + 50), (x0 + cel * i, y0 + h)], espessura=3, halo=False, textura=False))
        if fds and i >= 5:
            c.append(Mancha(ret(x0 + cel * i + 4, y0 + 54, cel - 8, h - 58), "apoio", 0.35, deslocamento=(0, 0)))
        c.append(Texto(d, cx, y0 + 90, "titulo", 34, "principal", "mm", halo=False))
        if i < dias:
            if marca == "check":
                c.append(Traco([(cx - 14, y0 + 158), (cx - 4, y0 + 174), (cx + 16, y0 + 138)], cor="apoio", espessura=7, halo=False))
            else:
                c += forma(ret(cx - 13, y0 + 142, 26, 26), "fundo", esp=4)
                c.append(Traco([(cx - 18, y0 + 174), (cx + 18, y0 + 136)], cor="apoio", espessura=6, halo=False))
    return Desenho(c)


@desenho("balde")
def balde():
    c = [Traco(elipse(0, -54, 78, 70, a0=math.pi, a1=2 * math.pi, n=18), espessura=7)]
    c += forma([(-80, -50), (80, -50), (60, 90), (-60, 90)], "objeto")
    c += forma(elipse(0, -50, 80, 16, n=24), "fundo", esp=6)
    c += [Traco([(-70, 10), (70, 10)], espessura=4, halo=False)]
    return Desenho(c)


@desenho("pizza")
def pizza():
    c = forma([(-70, -50), (70, -50), (0, 90)], "destaque")
    c += forma(ret_arred(-80, -70, 160, 30, 14), "objeto", esp=7)
    for x, y in ((-24, -20), (18, -6), (-2, 34)):
        c += forma(elipse(x, y, 12, 12, n=12), "apoio", esp=4)
    return Desenho(c)


@desenho("acucar")
def acucar():
    c = []
    for x, y in ((-70, 20), (10, 20), (-30, -50)):
        c += forma([(x - 34, y - 20), (x + 20, y - 34), (x + 50, y - 10), (x + 50, y + 44), (x - 4, y + 56), (x - 34, y + 34)], "fundo")
        c += [Traco([(x - 34, y - 20), (x - 4, y + 2), (x + 50, y - 10)], espessura=5, halo=False),
              Traco([(x - 4, y + 2), (x - 4, y + 56)], espessura=5, halo=False)]
        c += [Mancha(elipse(x + 18, y + 22, 3, 3, n=8), "principal", deslocamento=(0, 0)),
              Mancha(elipse(x + 8, y + 36, 3, 3, n=8), "principal", deslocamento=(0, 0))]
    return Desenho(c)


@desenho("opala")
def opala(combustivel=1.0):
    """Carrao antigo (sedan comprido) com o marcador de combustivel em cima."""
    corpo = [(-190, 40), (-190, -2), (-150, -10), (-96, -14), (-60, -56), (50, -56), (90, -14), (176, -8), (196, 6), (196, 40)]
    c = forma(corpo, "destaque")
    c += forma([(-50, -48), (-6, -48), (-6, -16), (-80, -16)], "fundo", esp=5) + forma([(6, -48), (44, -48), (76, -16), (6, -16)], "fundo", esp=5)
    c += [Traco([(-186, 14), (192, 14)], espessura=4, halo=False), Traco([(-196, 30), (-176, 30)], espessura=8),
          Traco([(178, 30), (200, 30)], espessura=8)]
    for x in (-118, 116):
        c += forma(elipse(x, 42, 30, 30, n=18), "principal", esp=6) + [Mancha(elipse(x, 42, 11, 11, n=10), "fundo", deslocamento=(0, 0))]
    gx, gy, r = 0, -110, 52  # marcador: meia lua de E (vazio) a F (cheio)
    c += forma(elipse(gx, gy, r + 10, r + 10, a0=math.pi, a1=2 * math.pi, n=20) + [(gx + r + 10, gy + 8), (gx - r - 10, gy + 8)], "fundo", esp=6)
    c += [Texto("E", gx - r + 8, gy - 6, "titulo", 26, "apoio", "mm", halo=False),
          Texto("F", gx + r - 8, gy - 6, "titulo", 26, "principal", "mm", halo=False)]
    a = math.pi + math.pi * (0.1 + 0.8 * combustivel)
    c.append(Traco([(gx, gy + 2), (gx + (r - 6) * math.cos(a), gy + 2 + (r - 6) * math.sin(a))], cor="apoio", espessura=7, halo=False))
    return Desenho(c)


@desenho("chope")
def chope():
    c = forma(ret_arred(-46, -50, 92, 130, 10), "destaque")
    c += [Traco(elipse(62, 14, 26, 34, a0=-1.5, a1=1.5, n=12), espessura=9)]
    espuma = elipse(-30, -54, 26, 22, a0=math.pi * 0.5, a1=math.pi * 1.6, n=10) + elipse(4, -66, 28, 24, a0=math.pi * 1.1, a1=math.pi * 1.9, n=10) \
        + elipse(34, -52, 22, 20, a0=math.pi * 1.4, a1=math.pi * 2.5, n=10)
    c += forma(espuma, "fundo", esp=6)
    c += [Traco([(-20, -20), (-20, 60)], cor="fundo", espessura=6, halo=False), Traco([(10, -20), (10, 60)], cor="fundo", espessura=6, halo=False)]
    return Desenho(c)


@desenho("pote_whey")
def pote_whey(transbordo=1.0):
    c = []
    if transbordo > 0.02:
        h = 70 * transbordo
        c += forma([(-90, -70)] + elipse(0, -70, 92, h, a0=math.pi, a1=2 * math.pi, n=18)[1:-1] + [(90, -70)], "fundo", esp=6)
        for x in (-112, 104):
            c += forma(elipse(x, 40 + 40 * transbordo, 22, 12 * transbordo + 2, n=12), "fundo", esp=5)
    c += forma(ret_arred(-96, -84, 192, 28, 8), "principal")
    c += forma([(-90, -56), (90, -56), (84, 100), (-84, 100)], "objeto")
    c += forma(ret(-70, -14, 140, 64), "fundo", esp=5) + [Texto("WHEY", 0, 18, "titulo", 44, "principal", "mm", halo=False)]
    return Desenho(c)


@desenho("brocolis")
def brocolis(teia_=False):
    c = forma([(-26, 20), (26, 20), (18, 120), (-18, 120)], "objeto")
    for x, y, r in ((-64, -10, 46), (60, -10, 46), (-30, -60, 52), (30, -62, 52), (0, -20, 56)):
        c += forma(elipse(x, y, r, r * 0.9, n=22), "objeto")
    c += [Traco([(0, 60), (-22, 10)], espessura=4, halo=False), Traco([(0, 70), (24, 14)], espessura=4, halo=False)]
    c += cara_triste(0, -30, 0.9)
    if teia_:
        c += teia(104, -104, 80, 1)
    return Desenho(c)


@desenho("barriga")
def barriga():
    """Abdomen feminino 'seco' com tanquinho, do top ate o cos do short (sem rosto nem pernas)."""
    esq = bezier((-100, -150), (-96, -80), (-82, -30), (-86, 30)) + bezier((-86, 30), (-90, 80), (-114, 116), (-120, 160))[1:]
    dir_ = [(-x, y) for x, y in esq]
    c = [Mancha(esq + dir_[::-1], "objeto"), Traco(esq, espessura=7), Traco(dir_, espessura=7)]
    c += forma([(-112, -170), (112, -170), (104, -136), (-104, -136)], "apoio", esp=6)  # top
    c += forma([(-108, 134), (108, 134), (114, 170), (-114, 170)], "principal", esp=6)  # cos do short
    c.append(Traco([(0, -118), (0, 62)], espessura=4, halo=False))  # linha do meio
    for y in (-78, -30, 18):  # gomos do tanquinho
        for sx in (-1, 1):
            c.append(Traco(bezier((sx * 8, y), (sx * 30, y - 8), (sx * 52, y - 4), (sx * 58, y + 6), n=10), espessura=4, halo=False))
    for sx in (-1, 1):  # linhas do V
        c.append(Traco(bezier((sx * 62, 50), (sx * 54, 84), (sx * 40, 112), (sx * 22, 128), n=10), espessura=4, halo=False))
    c.append(Traco(elipse(0, 82, 7, 10, n=12), fechado=True, espessura=4, halo=False))  # umbigo
    for x, y in ((-140, -60), (140, -10), (-136, 60)):  # brilho de "seco", feito a caneta
        c += [Traco([(x - 12, y), (x + 12, y)], cor="apoio", espessura=5, halo=False), Traco([(x, y - 12), (x, y + 12)], cor="apoio", espessura=5, halo=False)]
    return Desenho(c)


@desenho("balanca_cozinha")
def balanca_cozinha(teia_=False):
    c = forma(elipse(0, -64, 120, 20, n=26), "fundo", esp=6)
    c += [Traco([(0, -48), (0, -30)], espessura=8)]
    c += forma(ret_arred(-120, -30, 240, 100, 18), "objeto")
    c += forma(ret_arred(-60, -16, 120, 46, 8), "fundo", esp=5) + [Texto("0g", 0, 8, "titulo", 36, "principal", "mm", halo=False)]
    if teia_:
        c += teia(110, -26, 74, 1) + cara_triste(-80, 26, 0.5)
    return Desenho(c)


@desenho("prancheta")
def prancheta(texto="DIETA"):
    c = forma(ret_arred(-90, -120, 180, 240, 12), "objeto")
    c += forma(ret(-72, -96, 144, 200), "fundo", esp=5)
    c += forma(ret_arred(-36, -134, 72, 30, 8), "principal", esp=5)
    c.append(Texto(texto, 0, -62, "titulo", 36, "principal", "mm", halo=False))
    for y in (-26, 4, 34, 64):
        c.append(Traco(onda_pts(-54, 54, y, 3, 1.5, 12), espessura=4, halo=False))
    c.append(Traco(elipse(40, 76, 26, 16, n=14), fechado=True, cor="apoio", espessura=4, halo=False))
    return Desenho(c)


@desenho("rolinho")
def rolinho():
    c = forma(ret_arred(-90, -30, 180, 60, 28), "destaque")
    for x in range(-66, 80, 22):
        c.append(Mancha(elipse(x, 0, 6, 18, n=10), "principal", 0.6, deslocamento=(0, 0)))
    c += [Traco([(-90, 0), (-130, 0), (-130, 70)], espessura=10), Traco([(90, 0), (130, 0), (130, 70)], espessura=10),
          Traco([(-130, 70), (130, 70)], espessura=12)]
    return Desenho(c)


def _com_teia(nome, canto, cara):
    """Da a um desenho antigo o parametro teia_ (a piada do esquecido), sem mexer nele."""
    original = REGISTRO[nome]

    def f(teia_=False, **kw):
        d = original(**kw)
        return d + Desenho(teia(*canto, 1) + (cara_triste(*cara) if cara else [])) if teia_ else d
    REGISTRO[nome] = f


_com_teia("halter", (96, -48, 70), None)
_com_teia("garrafa_agua", (50, -86, 70), (0, -20, 0.7))
