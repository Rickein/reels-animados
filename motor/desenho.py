"""Desenho a mao em codigo: tracos tremidos, manchas de marca-texto e textos.

Tudo e desenhado em 2x e reduzido (sem serrilhado). A espessura e o tremor do traco sao sempre os do
estilo, qualquer que seja o tamanho do desenho: e isso que faz tudo parecer feito com a mesma caneta.
"""
import math
import random
from dataclasses import dataclass, field

from PIL import Image, ImageDraw

from motor.estilo import ESTILO, cor, fonte

SS = 2  # desenha em 2x e reduz


@dataclass
class Traco:
    pontos: list
    cor: str = "principal"
    espessura: float = None      # None = espessura do estilo
    fechado: bool = False
    halo: bool = True            # borda de papel por tras, para ler sobre o video
    tremor: float = None         # None = tremor do estilo
    textura: bool = True         # segunda passada fina, como caneta de verdade


@dataclass
class Mancha:
    pontos: list
    cor: str = "objeto"
    opacidade: float = 1.0
    deslocamento: tuple = None   # None = automatico (marca-texto sai um pouco da linha)
    tremor: float = None


@dataclass
class Texto:
    texto: str
    x: float = 0
    y: float = 0
    papel: str = "titulo"
    tamanho: float = 48
    cor: str = "principal"
    ancora: str = "mm"
    rotacao: float = 0.0
    halo: bool = True


@dataclass
class Desenho:
    camadas: list = field(default_factory=list)

    def __add__(self, outro):
        return Desenho(self.camadas + outro.camadas)


# ---------- geometria do traco ----------
def _chaikin(pts, fechado, voltas=2):
    for _ in range(voltas):
        n = len(pts)
        if n < 3:
            return pts
        novo = [] if fechado else [pts[0]]
        for i in range(n if fechado else n - 1):
            (x0, y0), (x1, y1) = pts[i], pts[(i + 1) % n]
            novo += [(0.75 * x0 + 0.25 * x1, 0.75 * y0 + 0.25 * y1), (0.25 * x0 + 0.75 * x1, 0.25 * y0 + 0.75 * y1)]
        if not fechado:
            novo.append(pts[-1])
        pts = novo
    return pts


def mao(pts, fechado, semente, amp, passo):
    """Subdivide, aplica um tremor suave (passeio aleatorio) e arredonda os cantos."""
    if len(pts) < 2:
        return list(pts)
    base = list(pts) + ([pts[0]] if fechado else [])
    sub = []
    for (x0, y0), (x1, y1) in zip(base, base[1:]):
        n = max(1, math.ceil(math.hypot(x1 - x0, y1 - y0) / passo))
        sub += [(x0 + (x1 - x0) * j / n, y0 + (y1 - y0) * j / n) for j in range(n)]
    if not fechado:
        sub.append(base[-1])
    r = random.Random(semente)
    ox = oy = 0.0
    offs = []
    for _ in sub:
        ox = ox * 0.7 + (r.random() * 2 - 1) * amp * 0.5
        oy = oy * 0.7 + (r.random() * 2 - 1) * amp * 0.5
        offs.append((ox, oy))
    if fechado and len(offs) > 1:  # tira o degrau onde a forma fecha
        dx, dy, n = offs[-1][0] - offs[0][0], offs[-1][1] - offs[0][1], len(offs)
        offs = [(a - dx * i / n, b - dy * i / n) for i, (a, b) in enumerate(offs)]
    return _chaikin([(x + a, y + b) for (x, y), (a, b) in zip(sub, offs)], fechado)


def comprimento(pts, fechado=False):
    seq = pts + ([pts[0]] if fechado and pts else [])
    return sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(seq, seq[1:]))


def cortar(pts, fechado, frac):
    """Trecho inicial do caminho com a fracao pedida do comprimento (para o traco 'se desenhar')."""
    seq = pts + ([pts[0]] if fechado and pts else [])
    if frac >= 1:
        return seq
    alvo, acc, out = comprimento(seq) * max(0.0, frac), 0.0, [seq[0]]
    for a, b in zip(seq, seq[1:]):
        d = math.hypot(b[0] - a[0], b[1] - a[1])
        if acc + d >= alvo:
            k = (alvo - acc) / d if d else 0
            out.append((a[0] + (b[0] - a[0]) * k, a[1] + (b[1] - a[1]) * k))
            return out
        acc += d
        out.append(b)
    return out


def _linha(draw, pts, rgba, w):
    if len(pts) < 2 or w <= 0:
        return
    draw.line(pts, fill=rgba, width=w, joint="curve")
    r = w / 2
    for x, y in (pts[0], pts[-1]):
        draw.ellipse([x - r, y - r, x + r, y + r], fill=rgba)


# ---------- texto ----------
def _texto_imagens(t: Texto, escala, halo_px, frac=1.0):
    """Imagens quadradas (tinta e halo) com o ponto de ancora no centro, ja giradas."""
    f = fonte(t.papel, round(t.tamanho * escala * SS))
    hw = round(halo_px * SS) if t.halo else 0
    l, tp, r, b = f.getbbox(t.texto, anchor=t.ancora, stroke_width=hw)
    meio = math.ceil(max(abs(l), abs(r), abs(tp), abs(b)) * 1.05) + 4
    lado = 2 * meio
    tinta = Image.new("RGBA", (lado, lado))
    halo = Image.new("RGBA", (lado, lado))
    ImageDraw.Draw(tinta).text((meio, meio), t.texto, font=f, anchor=t.ancora, fill=cor(t.cor))
    if hw:
        ImageDraw.Draw(halo).text((meio, meio), t.texto, font=f, anchor=t.ancora, fill=cor("fundo"),
                                  stroke_width=hw, stroke_fill=cor("fundo"))
    if frac < 1:  # escrevendo: revela da esquerda para a direita
        corte = round(meio + l + (r - l) * max(0.0, frac))
        for im in (tinta, halo):
            im.paste((0, 0, 0, 0), (corte, 0, lado, lado))
    if t.rotacao:
        tinta = tinta.rotate(-t.rotacao, resample=Image.BILINEAR)
        halo = halo.rotate(-t.rotacao, resample=Image.BILINEAR)
    return tinta, halo, meio


# ---------- colar no quadro ----------
def compor(base: Image.Image, img: Image.Image, x: int, y: int) -> None:
    """alpha_composite que aceita pedacos fora do quadro."""
    x0, y0 = max(0, x), max(0, y)
    x1, y1 = min(base.width, x + img.width), min(base.height, y + img.height)
    if x1 <= x0 or y1 <= y0:
        return
    base.alpha_composite(img.crop((x0 - x, y0 - y, x1 - x, y1 - y)), (x0, y0))


def colar(base, img, origem, x, y, sx=1.0, sy=1.0, rotacao=0.0, opacidade=1.0):
    """Cola um desenho com a origem dele em (x, y), aplicando escala (sx, sy), rotacao (graus) e opacidade."""
    if opacidade <= 0.01 or sx <= 0.01 or sy <= 0.01:
        return None
    ox, oy = origem
    if sx == 1 and sy == 1 and not rotacao:
        im, px, py = img, x - ox, y - oy
    else:
        meio = math.ceil(max(ox, img.width - ox, oy, img.height - oy)) + 2
        im = Image.new("RGBA", (2 * meio, 2 * meio))
        im.paste(img, (round(meio - ox), round(meio - oy)))
        if sx != 1 or sy != 1:
            im = im.resize((max(1, round(im.width * sx)), max(1, round(im.height * sy))), Image.BILINEAR)
        if rotacao:
            im = im.rotate(-rotacao, resample=Image.BILINEAR, expand=True)
        px, py = x - im.width / 2, y - im.height / 2
    if opacidade < 1:
        im = im.copy()
        im.putalpha(im.getchannel("A").point(lambda v: round(v * opacidade)))
    compor(base, im, round(px), round(py))
    return (round(px), round(py), round(px) + im.width, round(py) + im.height)


# ---------- renderizacao ----------
def render(d: Desenho, escala=1.0, semente=0, progresso=1.0):
    """Desenha e devolve (imagem RGBA, (ox, oy)): (ox, oy) e onde fica a origem (0, 0) do desenho.
    semente muda o tremor (use 0, 1, 2 em ciclo para a linha 'ferver'); progresso de 0 a 1 desenha aos poucos."""
    est = ESTILO["traco"]
    w_padrao, amp_padrao, passo = est["espessura"], est["tremor_px"], est["passo_px"]
    halo_extra = (est["halo"]["espessura"] - est["espessura"]) / 2
    seg = est["segunda_passada"]

    prep = []
    for i, c in enumerate(d.camadas):
        s = semente * 7919 + i * 101
        if isinstance(c, Traco):
            w = c.espessura or w_padrao
            pts = mao([(x * escala, y * escala) for x, y in c.pontos], c.fechado, s,
                      amp_padrao if c.tremor is None else c.tremor, passo)
            prep.append(["traco", c, pts, w, comprimento(pts, c.fechado)])
        elif isinstance(c, Mancha):
            desl = c.deslocamento if c.deslocamento is not None else ((0, 0) if c.cor == "fundo" else (5, 4))
            pts = mao([(x * escala, y * escala) for x, y in c.pontos], True, s,
                      amp_padrao * 0.6 if c.tremor is None else c.tremor, passo)
            prep.append(["mancha", c, [(x + desl[0], y + desl[1]) for x, y in pts], 0, 0])
        else:
            prep.append(["texto", c, None, 0, max(1, len(c.texto)) * c.tamanho * escala * 0.5])

    total = sum(p[4] for p in prep) or 1.0
    alvo = progresso * total
    inicios, acc = [], 0.0
    for p in prep:
        inicios.append(acc)
        acc += p[4]

    def frac_de(i):
        L = prep[i][4]
        return 1.0 if progresso >= 1 else (max(0.0, min(1.0, (alvo - inicios[i]) / L)) if L else float(alvo >= inicios[i]))

    # textos ja prontos (precisam entrar na caixa total)
    textos = {}
    for i, p in enumerate(prep):
        if p[0] == "texto":
            textos[i] = _texto_imagens(p[1], escala, halo_extra + 2, frac_de(i))

    # caixa que contem tudo
    xs, ys = [], []
    for i, p in enumerate(prep):
        if p[0] == "texto":
            meio = textos[i][2] / SS
            cx, cy = p[1].x * escala, p[1].y * escala
            xs += [cx - meio, cx + meio]
            ys += [cy - meio, cy + meio]
        else:
            m = p[3] / 2 + (halo_extra if p[0] == "traco" and p[1].halo else 0) + 2
            xs += [x - m for x, _ in p[2]] + [x + m for x, _ in p[2]]
            ys += [y - m for _, y in p[2]] + [y + m for _, y in p[2]]
    x0, y0 = math.floor(min(xs)) - 2, math.floor(min(ys)) - 2
    largura, altura = (math.ceil(max(xs)) + 2 - x0) * SS, (math.ceil(max(ys)) + 2 - y0) * SS
    para_px = lambda pts: [((x - x0) * SS, (y - y0) * SS) for x, y in pts]

    halo = Image.new("RGBA", (largura, altura))
    tinta = Image.new("RGBA", (largura, altura))
    textura = Image.new("RGBA", (largura, altura))
    dh, dt, dx = ImageDraw.Draw(halo), ImageDraw.Draw(tinta), ImageDraw.Draw(textura)
    tem_textura = False

    def assentar_textura():
        nonlocal tinta, dt, textura, dx, tem_textura
        if tem_textura:
            a = textura.getchannel("A").point(lambda v: round(v * seg["opacidade"]))
            textura.putalpha(a)
            tinta = Image.alpha_composite(tinta, textura)
            dt = ImageDraw.Draw(tinta)
            textura = Image.new("RGBA", (largura, altura))
            dx = ImageDraw.Draw(textura)
            tem_textura = False

    proximo_traco = {}
    for i in range(len(prep)):
        proximo_traco[i] = next((j for j in range(i + 1, len(prep)) if prep[j][0] == "traco"), None)

    for i, (tipo, c, pts, w, L) in enumerate(prep):
        f = frac_de(i)
        if tipo == "mancha":
            j = proximo_traco[i]
            vis = f if j is None else frac_de(j)  # a cor aparece enquanto o contorno e desenhado
            if vis <= 0:
                continue
            assentar_textura()
            camada = Image.new("RGBA", (largura, altura))
            ImageDraw.Draw(camada).polygon(para_px(pts), fill=cor(c.cor, c.opacidade * min(1.0, vis * 1.5)))
            tinta = Image.alpha_composite(tinta, camada)
            dt = ImageDraw.Draw(tinta)
        elif tipo == "traco":
            if f <= 0:
                continue
            trecho = para_px(cortar(pts, c.fechado, f))
            if c.halo:
                _linha(dh, trecho, cor("fundo"), round((w + 2 * halo_extra) * SS))
            _linha(dt, trecho, cor(c.cor), round(w * SS))
            if c.textura and w >= 4:
                fina = para_px(cortar(mao(pts, False, i + 31 + semente * 13, 1.2, 1e9), c.fechado, f))
                _linha(dx, fina, cor(c.cor), round(w * seg["espessura_rel"] * SS))
                tem_textura = True
        else:
            if f <= 0:
                continue
            assentar_textura()
            img_t, img_h, meio = textos[i]
            pos = (round((c.x * escala - x0) * SS) - meio, round((c.y * escala - y0) * SS) - meio)
            halo.alpha_composite(img_h, dest=pos)
            tinta.alpha_composite(img_t, dest=pos)
            dt = ImageDraw.Draw(tinta)
    assentar_textura()

    # BOX = media exata de cada bloco 2x2 (o LANCZOS criava um brilho quase branco junto das linhas)
    final = Image.alpha_composite(halo, tinta).resize((largura // SS, altura // SS), Image.BOX)
    caixa = final.getbbox()  # corta a sobra transparente (os textos giram dentro de quadrados folgados)
    if not caixa:
        return final, (-x0, -y0)
    return final.crop(caixa), (-x0 - caixa[0], -y0 - caixa[1])
