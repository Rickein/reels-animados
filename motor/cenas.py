"""Cenas: o roteiro vira atores animados. Cada desenho entra na palavra certa e fica longe do rosto.

Cada cena tem uma funcao desenhar(quadro, t), com t em segundos do audio. Os desenhos de uma cena
continuam na tela nas cenas seguintes do mesmo capitulo, ate sairem ou ate a transicao cobrir tudo.
"""
import math

from motor import tempo as T
from motor.biblioteca import ancoras, obter
from motor.desenho import colar
from motor.estilo import ESTILO
from motor.roteiro import transicoes as calcular_transicoes

QW, QH = ESTILO["quadro"]["largura"], ESTILO["quadro"]["altura"]
MOV = ESTILO["movimento"]
DUR = MOV["duracoes"]
ENT = MOV["curvas"]["entrada"]
SAIDA = MOV["curvas"]["saida"]
IMPACTO = MOV["impacto"]
TREME = MOV["objeto_tremendo"]
ZONAS = ESTILO["zonas"]
SEGURA = ESTILO["areas_seguras"]
_cx_leg, _cy_leg = ESTILO["legenda"]["caixa"]["centro"]
TOPO_LEGENDA = _cy_leg - ESTILO["legenda"]["caixa"]["altura"] / 2 - 10
MARGEM = 16

_, _alt_leg = ESTILO["legenda"]["caixa"]["centro"], ESTILO["legenda"]["caixa"]["altura"]
BASE_LEGENDA = _cy_leg + _alt_leg / 2 + 10
# limites com folga para o "quique" das entradas nao encostar nas bordas
LIMITES_CIMA = (MARGEM, SEGURA["topo"] + 14, QW - MARGEM, TOPO_LEGENDA)            # acima da legenda
LIMITES_BAIXO = (40, BASE_LEGENDA + 22, QW - 40, QH - SEGURA["base"] - 6)          # entre a legenda e a base
BOTOES_REELS = (QW - SEGURA["direita"], 1000, QW, QH)
FOLGA = 12

ENTRADAS_POP = {"pop", "borrifar", "procurar", "balancar", "balancar_e_circular", "acender"}
# estado "mais largo" de cada desenho: o layout reserva espaco para ele (nada corta quando anima)
PARAMS_MAXIMOS = {
    "espelho": {"espremer": 1.0}, "megafone": {"ondas": 1.0}, "borrifador": {"borrifo": 1.0},
    "ring_light": {"brilho": 1.0}, "biceps": {"brilho": 1.0}, "lampada": {"acesa": 1.0},
    "fabrica": {"fumaca": 1.0}, "gotas_suor": {"n": 6}, "pao": {"suor": 3, "boina": True},
    "contador": {"concluido": True},
    "prato": {"teia_": True}, "brocolis": {"teia_": True}, "balanca_cozinha": {"teia_": True},
    "halter": {"teia_": True}, "garrafa_agua": {"teia_": True},
    "calendario": {"dias": 5, "fds": True}, "riscos": {"n": 20}, "pote_whey": {"transbordo": 1.0},
}
FATOR_FILHO = {"dentro": 0.55, "acima": 0.6, "abaixo": 0.55}
PARAMS_INICIAIS = {
    "balanca": {"inclinacao": -0.3, "coracao": False},
    "transferidor": {"angulo": 0, "texto": ""},
    "texto_mao": {"rotacao": -3.0},
    "pao": {"suor": 0},
}
MEDROSOS = {"pao", "gotas_suor"}
CHAVES_DO_ROTEIRO = {"id", "desenho", "zona", "slot", "escala", "entra", "acoes", "sai", "nota", "cobrir", "tremendo"}


def _slot(caixa, slot, empilhar=False):
    """Fatia de uma caixa: divide na direcao mais comprida (ou sempre de cima para baixo, numa lista)."""
    x0, y0, x1, y1 = caixa
    i, n = slot
    if x1 - x0 >= y1 - y0 and not empilhar:
        return (x0 + (x1 - x0) * i / n, y0, x0 + (x1 - x0) * (i + 1) / n, y1)
    return (x0, y0 + (y1 - y0) * i / n, x1, y0 + (y1 - y0) * (i + 1) / n)


def _sobrepoe(a, b, folga=0):
    return a[0] < b[2] + folga and a[2] > b[0] - folga and a[1] < b[3] + folga and a[3] > b[1] - folga


def _uniao(a, b):
    return (min(a[0], b[0]), min(a[1], b[1]), max(a[2], b[2]), max(a[3], b[3]))


def _area_comum(a, b):
    return max(0.0, min(a[2], b[2]) - max(a[0], b[0])) * max(0.0, min(a[3], b[3]) - max(a[1], b[1]))


def resolver_posicao(caixa, obstaculos, limites):
    """Menor deslocamento (dx, dy) e reducao k que deixam a caixa dentro dos limites e sem encostar em
    nenhum obstaculo. Os candidatos sao as bordas dos obstaculos e dos limites (busca pequena e exata).
    Se nao houver lugar limpo, fica onde encosta menos (o primeiro obstaculo, a cabeca, pesa 4x)."""
    lx0, ly0, lx1, ly1 = limites
    melhor, menos_ruim = None, None
    for k in (1.0, 0.85, 0.72, 0.6):
        cx, cy = (caixa[0] + caixa[2]) / 2, (caixa[1] + caixa[3]) / 2
        w, h = (caixa[2] - caixa[0]) * k, (caixa[3] - caixa[1]) * k
        x0, y0 = cx - w / 2, cy - h / 2
        dxs, dys = {0.0, lx0 - x0, lx1 - (x0 + w)}, {0.0, ly0 - y0, ly1 - (y0 + h)}
        for o in obstaculos:
            dxs |= {o[0] - (x0 + w) - FOLGA, o[2] - x0 + FOLGA}
            dys |= {o[1] - (y0 + h) - FOLGA, o[3] - y0 + FOLGA}
        for dx in dxs:
            nx0, nx1 = x0 + dx, x0 + w + dx
            if nx0 < lx0 - 0.5 or nx1 > lx1 + 0.5:
                continue
            for dy in dys:
                ny0, ny1 = y0 + dy, y0 + h + dy
                if ny0 < ly0 - 0.5 or ny1 > ly1 + 0.5:
                    continue
                nova = (nx0, ny0, nx1, ny1)
                if any(_sobrepoe(nova, o, FOLGA - 1) for o in obstaculos):
                    encosta = sum(_area_comum(nova, o) * (4 if i == 1 else 1) for i, o in enumerate(obstaculos))
                    if menos_ruim is None or encosta < menos_ruim[0]:
                        menos_ruim = (encosta, dx, dy, k)
                    continue
                custo = math.hypot(dx, dy) + (1 - k) * 900
                if melhor is None or custo < melhor[0]:
                    melhor = (custo, dx, dy, k)
        if melhor and melhor[0] < (1 - k + 0.15) * 900:
            break
    escolha = melhor or menos_ruim
    return (escolha[1], escolha[2], escolha[3]) if escolha else (0.0, 0.0, 1.0)


class Ator:
    """Um desenho do roteiro com sua linha do tempo (entra, acoes, sai)."""

    def __init__(self, el, palavras, ordem):
        self.el, self.id, self.nome, self.ordem = el, el["id"], el["desenho"], ordem
        quando = lambda g: round(palavras[g["em"]]["inicio"] + g.get("atraso", 0.0), 3)
        self.t_entra, self.anim_entra = quando(el["entra"]), el["entra"]["anim"]
        self.impacto_entra = el["entra"].get("impacto", False)
        self.acoes = [(quando(a), a["anim"], a.get("impacto", False)) for a in el.get("acoes", [])]
        self.t_sai = quando(el["sai"]) if "sai" in el else None
        self.anim_sai = el["sai"]["anim"] if "sai" in el else None
        self.t_some = None  # definido pelo Filme (fim da saida ou meio da transicao)
        self.params = dict(PARAMS_INICIAIS.get(self.nome, {}))
        for k, v in el.items():  # o que nao e do roteiro vai como parametro do desenho (texto, tamanho, numero...)
            if k not in CHAVES_DO_ROTEIRO:
                self.params["rotulo" if (k == "texto" and self.nome == "balanca") else k] = tuple(v) if isinstance(v, list) else v
        self.medroso = self.nome in MEDROSOS or el.get("tremendo", False)
        self.zona = el["zona"]
        self.slot = el.get("slot", [0, 1])
        self.escala_extra = el.get("escala", 1.0)
        self.escala = 1.0
        self.escala_base = 1.0   # escala da zona, antes do 'escala' do roteiro (filhos usam esta)
        self.fixo = False        # encaixado num lugar exato (ex.: dentro do cartao): nao desvia
        self.pos = None          # onde fica a origem do desenho (layout fixo)
        self.pai = None          # (ator, relacao) quando o desenho encaixa em outro
        self.caixa_ref = None    # caixa do desenho relativa a origem, na escala final
        self.caixa_grupo = None  # caixa_ref + filhos pendurados + folga de movimento (o que o layout reserva)
        animacoes = [self.anim_entra] + [an for _, an, _ in self.acoes]
        self.folga_x = 44 if "procurar" in animacoes else 0

    # ---------- estado animado ----------
    def estado(self, t):
        """None se nao aparece; senao params do desenho + transformacoes do instante t."""
        if t < self.t_entra or (self.t_some is not None and t >= self.t_some):
            return None
        td = T.em_dois(t)
        p = dict(self.params)
        e = {"progresso": 1.0, "sx": 1.0, "sy": 1.0, "rot": 0.0, "dx": 0.0, "dy": 0.0, "opac": 1.0,
             "extras": [], "orbita": None, "voar": None, "semente_extra": 0}
        u, ud, a = t - self.t_entra, td - self.t_entra, self.anim_entra

        def escalar(k):
            e["sx"] *= k
            e["sy"] *= k

        # entrada
        if a in ENTRADAS_POP:
            escalar(max(0.0, T.back_out(T.progresso(u, 0, ENT["duracao"]), ENT["passada"])))
        if a == "colar":
            pk = T.progresso(u, 0, 0.22)
            escalar(1 + (0.05 if "cobrir" in self.el else 0.25) * (1 - T.back_out(pk, 2.0)))
            if "cobrir" not in self.el:  # girado, o cartao deixaria pontas do titulo antigo a mostra
                e["rot"] -= 8 * (1 - T.ease_out(pk))
            # o que cobre texto antigo aparece inteiro ja no primeiro quadro
            e["opac"] = 1.0 if "cobrir" in self.el else T.progresso(u, 0, 0.06)
        if a in ("cair", "fincar"):
            e["dy"] -= 320 * (1 - T.back_out(T.progresso(u, 0, 0.4), 1.4))
            if a == "fincar" and u > 0.4:
                s = 0.15 * T.mola(u - 0.4, 1, 8, 20)
                e["sx"], e["sy"] = e["sx"] * (1 + s), e["sy"] * (1 - s)
        if a == "desenhar":
            e["progresso"] = T.in_out(T.progresso(ud, 0, 0.45))
        if a == "escrever":
            e["progresso"] = T.in_out(T.progresso(ud, 0, DUR["escrever_texto"]))
        if a == "escrever_e_circular":
            e["progresso"] = T.in_out(T.progresso(ud, 0, 0.45))
            if ud > 0.45:
                e["extras"].append(("circulo", T.in_out(T.progresso(ud, 0.45, DUR["circulo"]))))
        if a == "subir":
            pk = T.progresso(u, 0, 0.6)
            e["dy"] += 140 * (1 - T.ease_out(pk)) + 6 * math.sin(2 * math.pi * u / 1.6)
            e["opac"] = pk
        if a == "borrifar":
            p["borrifo"] = T.clamp(((ud - 0.1) % 0.8) / 0.35) if ud > 0.1 else 0.0
        if a == "procurar":
            e["dx"] += 30 * math.sin(2 * math.pi * u / 1.2)
        if a == "desenrolar":
            p["comprimento"] = 0.25 + 0.75 * T.back_out(T.progresso(ud, 0, 0.45), 1.2)
        if a in ("balancar", "balancar_e_circular"):
            e["rot"] += 14 * T.mola(u, 1, 3, 9)
        if a == "balancar_e_circular" and ud > 0.2:
            e["extras"].append(("circulo", T.in_out(T.progresso(ud, 0.2, DUR["circulo"]))))
        if a == "acender":
            p["acesa"] = T.progresso(ud, 0, 0.3)
        if a == "contar_numero":  # numero grande que conta de 0 ate o valor (ou so aparece, se nao for numero)
            escalar(max(0.0, T.back_out(T.progresso(u, 0, ENT["duracao"]), ENT["passada"])))
            alvo = str(self.params.get("texto", ""))
            if alvo.isdigit():
                p["texto"] = str(round(int(alvo) * T.ease_out(T.progresso(ud, 0, 0.5))))
        if self.medroso and u > 0.3:
            fase = int(td * T.FPS_DESENHO)
            e["dx"] += math.sin(fase * 2.1) * TREME["amplitude_px"]

        # acoes
        for ta, anim, _ in self.acoes:
            if t < ta:
                continue
            u, ud = t - ta, td - ta
            if anim == "contar":
                p["ponteiro"] = 2 * math.pi * ud / 1.5
            elif anim == "tremer":
                dx, dy = T.tremida(t, ta, 0.5, TREME["amplitude_px"] + 2)
                e["dx"] += dx
                e["dy"] += dy
            elif anim == "espiral":
                p["espiral"] = T.in_out(T.progresso(ud, 0, 0.5))
                e["rot"] -= 90 * u
            elif anim in ("apertar", "receber_selo", "virar_pao_frances"):
                s = 0.22 * T.mola(u, 1, 7, 18)
                e["sx"], e["sy"] = e["sx"] * (1 + s), e["sy"] * (1 - s)
                if anim == "virar_pao_frances":
                    p["tipo"] = "frances"
            elif anim in ("pingar", "crescer", "flexionar", "bater", "boina", "marcar_concluido", "multiplicar"):
                forca = {"bater": 0.35, "crescer": 0.0}.get(anim, 0.12)
                escalar(1 + forca * T.mola(u, 1, 7, 16))
                if anim == "crescer":
                    escalar(1 + 0.2 * T.ease_out(T.progresso(u, 0, 0.3)))
                if anim == "pingar":
                    e["dy"] += 10 * T.mola(u, 1, 6, 10)
                if anim == "multiplicar":
                    p["n"] = 6
                if anim == "boina":
                    p["boina"] = True
                if anim == "marcar_concluido":
                    p["concluido"] = True
            elif anim == "espremer_reflexo":
                p["espremer"] = min(1.0, T.back_out(T.progresso(ud, 0, 0.25), 2.0))
            elif anim == "circular":
                e["extras"].append(("circulo", T.in_out(T.progresso(ud, 0, DUR["circulo"]))))
            elif anim == "gritar":
                p["ondas"] = round(0.35 + 0.65 * abs(math.sin(math.pi * ud / 0.45)), 2)
                escalar(1 + 0.08 * T.mola(u, 1, 6, 16))
            elif anim == "tombar":
                p["inclinacao"] = round(-0.55 + 0.25 * T.mola(ud, 1, 5, 14), 3)
            elif anim == "voar_longe":
                k = u / 0.8
                if k >= 1:
                    return None
                e["dx"] += 520 * k
                e["dy"] += -700 * k + 500 * k * k
                e["rot"] += 600 * k
            elif anim == "riscar":
                e["extras"].append(("riscar", T.in_out(T.progresso(ud, 0, DUR["riscar_linha"]))))
            elif anim == "suar_mais":
                p["suor"] = 3
                e["dx"] += math.sin(int(td * T.FPS_DESENHO) * 2.7) * 3
            elif anim == "desenrolar_longo":
                p["comprimento"] = 1.0 + 1.6 * T.back_out(T.progresso(ud, 0, 0.45), 1.2)
            elif anim == "malabarismo":
                e["orbita"] = (ta, u)
                escalar(1 - 0.4 * T.ease_out(T.progresso(u, 0, 0.3)))  # encolhem para caber girando
            elif anim == "quase_cair":
                m = T.mola(u, 1, 5, 9)
                e["dy"] += 70 * abs(m)
                e["rot"] += 20 * m
            elif anim == "despencar":
                e["orbita"] = None if e["orbita"] is None else (e["orbita"][0], ta - e["orbita"][0])
                e["dy"] += 2200 * u * u
                e["rot"] += 260 * u
                if e["dy"] > QH:
                    return None
            elif anim == "procurar":
                e["dx"] += 40 * math.sin(2 * math.pi * u / 0.8)
            elif anim == "medir_angulo":
                p["angulo"] = round(45 * T.in_out(T.progresso(ud, 0, 0.35)))
                p["texto"] = "45°" if ud > 0.3 else ""
            elif anim == "brilhar":
                p["brilho"] = round(T.progresso(ud, 0, 0.2) * (0.7 + 0.3 * abs(math.sin(math.pi * ud / 0.4))), 2)
            elif anim == "levantar":  # na faixa abaixo da legenda o espaco e curto
                e["dy"] -= (16 if self.zona == "abaixo_legenda" else 60) * abs(math.sin(math.pi * u / 0.55))
            elif anim == "fumegar":
                p["fumaca"] = T.progresso(ud, 0, 0.5)
            elif anim == "marcar":
                p["marcado"] = True
                escalar(1 + 0.12 * T.mola(u, 1, 7, 16))
            elif anim == "pulsar":
                escalar(1 + 0.07 * math.sin(2 * math.pi * u / 0.6))
            elif anim == "abandonar":  # a piada do esquecido: teia de aranha e cara triste
                p["teia_"] = True
                escalar(1 + 0.12 * T.mola(u, 1, 7, 16))
                e["rot"] += 4 * T.ease_out(T.progresso(u, 0, 0.4))
            elif anim == "correr":
                e["dy"] -= 26 * abs(math.sin(2 * math.pi * ud / 0.36))
                e["rot"] += 5 * math.sin(2 * math.pi * ud / 0.36)
            elif anim == "rolar":
                e["dx"] += 18 * math.sin(2 * math.pi * ud / 0.9)
            elif anim == "esvaziar":
                p["combustivel"] = round(1 - T.in_out(T.progresso(ud, 0, 0.8)), 2)
            elif anim == "marcar_dias":
                p["dias"] = min(5, int(ud / 0.12) + 1)
            elif anim == "pintar_fds":
                p["fds"] = True
                escalar(1 + 0.1 * T.mola(u, 1, 7, 16))
            elif anim == "contar_riscos":
                p["n"] = min(20, int(ud / 0.035) + 1)
            elif anim == "transbordar":
                p["transbordo"] = round(min(1.0, T.back_out(T.progresso(ud, 0, 0.4), 1.6)), 2)
                escalar(1 + 0.1 * T.mola(u, 1, 7, 16))
            elif anim.startswith("voar_e_colar"):
                e["voar"] = (anim.split(":")[1], T.in_out(T.progresso(u, 0, 0.4)))

        # saida
        if self.t_sai is not None and t >= self.t_sai:
            u = t - self.t_sai
            if self.anim_sai == "borracha":
                e["progresso"] = min(e["progresso"], 1 - T.in_out(T.progresso(td - self.t_sai, 0, SAIDA["duracao"])))
            elif self.anim_sai == "puf":
                pk = T.progresso(u, 0, 0.2)
                escalar(1 + 0.25 * pk)
                e["opac"] *= 1 - pk
        e["params"] = p
        return e

    def gatilhos(self):
        """(instante, animacao, impacto) de tudo que este ator faz (para som e camera)."""
        lista = [(self.t_entra, self.anim_entra, self.impacto_entra)] + list(self.acoes)
        if self.t_sai is not None:
            lista.append((self.t_sai, self.anim_sai, False))
        return lista


class Cena:
    def __init__(self, filme, dados, inicio, fim):
        self.filme, self.id, self.inicio, self.fim = filme, dados["id"], inicio, fim
        self.metafora = dados["metafora"]

    def desenhar(self, quadro, t):
        """Desenha esta cena no instante t (tudo que estiver vivo na tela)."""
        self.filme.desenhar_atores(quadro, t)


class Filme:
    def __init__(self, roteiro, palavras, trilha_rosto):
        self.roteiro, self.palavras, self.trilha = roteiro, palavras, trilha_rosto
        from motor.legenda import caixa_ocupada
        leg = caixa_ocupada(roteiro.get("opcoes", {}))
        self.limites_cima = (LIMITES_CIMA[0], LIMITES_CIMA[1], LIMITES_CIMA[2], leg[1] - 30)
        faixa = roteiro.get("opcoes", {}).get("faixa_central")  # [x0, x1]: desenhos nunca vao para as laterais
        if faixa:
            self.limites_cima = (faixa[0], self.limites_cima[1], faixa[1], self.limites_cima[3])
        self.limites_baixo = (LIMITES_BAIXO[0], leg[3] + 32, LIMITES_BAIXO[2], LIMITES_BAIXO[3])
        self.transicoes = calcular_transicoes(roteiro, palavras, ESTILO["transicao"]["duracao"])
        self.atores = [Ator(el, palavras, i) for i, el in enumerate(roteiro["elementos"])]
        self.por_id = {a.id: a for a in self.atores}
        for a in self.atores:
            if a.t_sai is not None:
                a.t_some = a.t_sai + (SAIDA["duracao"] if a.anim_sai == "borracha" else 0.2) + 0.02
            else:
                prox = [tr for tr in self.transicoes if tr["inicio"] > a.t_entra]
                a.t_some = (prox[0]["inicio"] + prox[0]["fim"]) / 2 if prox else roteiro["fim"] + 1
        self._layout()
        cenas = roteiro["cenas"]
        self.cenas = []
        for k, c in enumerate(cenas):
            ini = palavras[c["palavras"][0]]["inicio"] if k else roteiro["inicio"]
            fim = palavras[cenas[k + 1]["palavras"][0]]["inicio"] if k + 1 < len(cenas) else roteiro["fim"]
            self.cenas.append(Cena(self, c, ini, fim))
        self.impactos = sorted({round(t, 3) for a in self.atores for t, _, imp in a.gatilhos() if imp})

    # ---------- layout ----------
    def _layout(self):
        self._memo = {}
        self._cab_vida = {}
        for a in self.atores:
            if a.zona.startswith("de:"):
                continue  # seta entre dois desenhos: calculada a cada quadro
            img, (ox, oy) = obter(a.nome, **a.params)
            caixa1 = (-ox, -oy, img.width - ox, img.height - oy)  # na escala 1
            if a.nome in PARAMS_MAXIMOS:
                img2, (ox2, oy2) = obter(a.nome, **{**a.params, **PARAMS_MAXIMOS[a.nome]})
                caixa1 = _uniao(caixa1, (-ox2, -oy2, img2.width - ox2, img2.height - oy2))
            w, h = caixa1[2] - caixa1[0], caixa1[3] - caixa1[1]
            if "cobrir" in a.el:  # cartao que esconde o titulo antigo: do tamanho exato da area
                x0, y0, x1, y1 = a.el["cobrir"]
                a.params.update(largura=x1 - x0, altura=y1 - y0)
                a.escala, a.pos = 1.0, ((x0 + x1) / 2, (y0 + y1) / 2)
                a.caixa_ref = (-(x1 - x0) / 2, -(y1 - y0) / 2, (x1 - x0) / 2, (y1 - y0) / 2)
                continue
            if a.nome == "contador":  # canto de cima: o lado em que a cabeca menos atrapalha neste capitulo
                x0, y0, x1, y1 = ZONAS["topo_esquerdo"]
                cy = (y0 + y1) / 2
                lados = [(x0 + 26, cy), (QW - 30 - caixa1[2], cy)]

                def encostes(pos):
                    caixa = (pos[0] + caixa1[0], pos[1] + caixa1[1], pos[0] + caixa1[2], pos[1] + caixa1[3])
                    passos = int((min(a.t_some, self.roteiro["fim"]) - a.t_entra) * 5) + 1
                    return sum(1 for i in range(passos)
                               if (cab := self.trilha.cabeca_em(a.t_entra + i / 5)) and _sobrepoe(caixa, cab))

                a.escala, a.caixa_ref = 1.0, caixa1
                a.pos = min(lados, key=encostes) if self.trilha else lados[0]
                continue
            rel, _, alvo = a.zona.partition(":")
            if alvo:
                pai = self.por_id[alvo]
                if pai.caixa_ref and "cobrir" in pai.el:  # encaixa num cartao: o cartao vira a zona
                    cx, cy = pai.pos
                    zona = _slot((cx + pai.caixa_ref[0] + 14, cy + pai.caixa_ref[1] + 10, cx + pai.caixa_ref[2] - 14, cy + pai.caixa_ref[3] - 10), a.slot)
                    self._encaixar(a, zona, caixa1, w, h)
                    a.fixo = True
                    continue
                a.pai = (pai, rel)
                if a.nome in ("texto_mao", "item_lista"):  # texto pendurado mantem o tamanho de letra pedido
                    a.escala = a.escala_extra
                else:
                    a.escala = pai.escala_base * FATOR_FILHO.get(rel, 0.55) * a.escala_extra
                a.caixa_ref = tuple(v * a.escala for v in caixa1)
                continue
            if a.zona == "perto_da_cabeca":
                a.escala = 0.8 * a.escala_extra
                a.caixa_ref = tuple(v * a.escala for v in caixa1)
                continue
            self._encaixar(a, _slot(ZONAS[a.zona], a.slot, empilhar=a.nome == "item_lista"), caixa1, w, h)
        self._alinhar_listas()
        self._montar_grupos()

    def _alinhar_listas(self):
        """Itens de uma mesma lista: mesmo tamanho de letra e todos alinhados pela esquerda."""
        grupos = {}
        for a in self.atores:
            if a.nome == "item_lista" and a.pos and not a.pai:
                grupos.setdefault((a.zona, a.slot[1], a.id.rsplit("_", 1)[0]), []).append(a)
        for (zona, _, _), itens in grupos.items():
            k = min(i.escala_base for i in itens)
            larguras = []
            for i in itens:
                f = k / i.escala_base
                i.caixa_ref = tuple(v * f for v in i.caixa_ref)
                i.escala, i.escala_base = i.escala * f, k
                larguras.append(i.caixa_ref[2] - i.caixa_ref[0])
            x0, _, x1, _ = ZONAS[zona]
            esquerda = (x0 + x1) / 2 - max(larguras) / 2
            for i in itens:
                _, y_slot0, _, y_slot1 = _slot(ZONAS[zona], i.slot, empilhar=True)
                i.pos = (esquerda - i.caixa_ref[0], (y_slot0 + y_slot1) / 2 - (i.caixa_ref[1] + i.caixa_ref[3]) / 2)

    def _montar_grupos(self):
        """O lugar reservado por um desenho inclui o que fica pendurado nele (ex.: lampada acima da fabrica)
        e a folga do movimento dele (ex.: lupa que procura de um lado para o outro)."""
        for a in self.atores:
            if a.caixa_ref:
                cr = a.caixa_ref
                a.caixa_grupo = (cr[0] - a.folga_x, cr[1], cr[2] + a.folga_x, cr[3])
        for a in self.atores:
            if not a.pai or a.pai[1] == "dentro" or not a.caixa_ref:
                continue
            pai, rel = a.pai
            raiz = pai
            while raiz.pai:
                raiz = raiz.pai[0]
            if raiz.caixa_grupo is None:
                continue
            anc = ancoras(pai.nome, **pai.params)
            if rel in anc:
                ox, oy = anc[rel][0] * pai.escala, anc[rel][1] * pai.escala
            else:
                ox, oy = self._encaixe(pai, a, rel, 0.0, 0.0)
            filho = (ox + a.caixa_ref[0], oy + a.caixa_ref[1], ox + a.caixa_ref[2], oy + a.caixa_ref[3])
            raiz.caixa_grupo = _uniao(raiz.caixa_grupo, filho)

    def _encaixar(self, a, zona, caixa1, w, h):
        x0, y0, x1, y1 = zona
        maximo = ZONAS["ampliacao_max"] * (1.5 if a.zona == "palco" else 1.0)  # sem rosto, o desenho pode crescer
        k = min((x1 - x0) * ZONAS["preenchimento"] / w, (y1 - y0) * ZONAS["preenchimento"] / h, maximo)
        a.escala_base = k
        a.escala = k * a.escala_extra
        a.caixa_ref = tuple(v * a.escala for v in caixa1)
        meio_x, meio_y = (a.caixa_ref[0] + a.caixa_ref[2]) / 2, (a.caixa_ref[1] + a.caixa_ref[3]) / 2
        a.pos = ((x0 + x1) / 2 - meio_x, (y0 + y1) / 2 - meio_y)

    def _livre(self, a):
        """Ator posicionado por zona (os outros seguem o pai, a cabeca ou tem lugar fixo)."""
        return a.pos is not None and not a.pai and not a.fixo and "cobrir" not in a.el and a.nome != "contador"

    def ajuste(self, a, t):
        """(dx, dy, k) para o ator nao encostar no rosto, no contador nem nos desenhos que chegaram antes.
        Quem chegou antes tem prioridade e reserva o lugar durante toda a vida dele (nada pula na tela)."""
        chave = (a.id, round(t * 30))
        if chave in self._memo:
            return self._memo[chave]
        x, y = a.pos
        cr = a.caixa_grupo
        caixa = (x + cr[0], y + cr[1], x + cr[2], y + cr[3])
        abaixo = a.zona == "abaixo_legenda"
        obst = [BOTOES_REELS]
        janela = self.roteiro.get("opcoes", {}).get("desvio_janela", 99)
        obst += [c for (t0, t1, c) in getattr(self, "obstaculos_extra", ()) if t0 < a.t_entra + janela and t1 > a.t_entra]
        cab = self._cabeca_na_vida(a) if self.roteiro.get("opcoes", {}).get("desvio_estavel") else (self.trilha.cabeca_em(t) if self.trilha else None)
        if cab:
            obst.append(cab)
        for b in self.atores:
            if b is a or b.ordem > a.ordem or b.t_some <= a.t_entra or b.t_entra >= a.t_some:
                continue
            if b.nome == "contador" or "cobrir" in b.el:
                bx, by = b.pos
                obst.append((bx + b.caixa_ref[0], by + b.caixa_ref[1], bx + b.caixa_ref[2], by + b.caixa_ref[3]))
            elif b.zona == "perto_da_cabeca":
                c = self.caixa_atual(b, min(max(t, b.t_entra), b.t_some - 0.01))
                if c:
                    obst.append(c)
            elif self._livre(b):
                tb = min(max(t, b.t_entra), b.t_some - 0.01)
                dx, dy, k = self.ajuste(b, tb)
                bx, by = b.pos[0] + dx, b.pos[1] + dy
                bc = b.caixa_grupo
                meio = ((bc[0] + bc[2]) / 2, (bc[1] + bc[3]) / 2)
                obst.append((bx + meio[0] + (bc[0] - meio[0]) * k, by + meio[1] + (bc[1] - meio[1]) * k,
                             bx + meio[0] + (bc[2] - meio[0]) * k, by + meio[1] + (bc[3] - meio[1]) * k))
        r = resolver_posicao(caixa, obst, self.limites_baixo if abaixo else self.limites_cima)
        self._memo[chave] = r
        return r

    def _cabeca_na_vida(self, a):
        """Uniao das caixas da cabeca durante toda a vida do ator: o desenho escolhe um lugar e fica nele."""
        if not self.trilha:
            return None
        if a.id not in self._cab_vida:
            caixas, t = [], a.t_entra
            janela = self.roteiro["opcoes"].get("desvio_janela", 99)  # so os primeiros segundos de vida contam
            fim = min(a.t_some, self.roteiro["fim"], a.t_entra + janela)
            while t < fim:
                c = self.trilha.cabeca_em(t)
                if c:
                    caixas.append(c)
                t += 0.2
            apara = self.roteiro["opcoes"].get("aparar_testa", 0.0)  # fração do alto da caixa que pode ser coberta (cabelo)
            self._cab_vida[a.id] = (min(c[0] for c in caixas), min(c[1] + (c[3] - c[1]) * apara for c in caixas),
                                    max(c[2] for c in caixas), max(c[3] for c in caixas)) if caixas else None
        return self._cab_vida[a.id]

    def posicao_base(self, a, t, params):
        """Onde a origem do ator fica agora (antes das animacoes de deslocamento)."""
        if a.pai:
            pai, rel = a.pai
            est_pai = pai.estado(t)
            px, py = self.posicao_final(pai, t, est_pai) if est_pai else self.posicao_base(pai, t, pai.params)
            anc = ancoras(pai.nome, **(est_pai["params"] if est_pai else pai.params))
            if rel in anc:
                ax, ay = anc[rel]
                return px + ax * pai.escala, py + ay * pai.escala
            return self._encaixe(pai, a, rel, px, py)
        if a.zona == "perto_da_cabeca":  # do lado da cabeca que estiver livre (direita, esquerda ou em cima)
            cab = self.trilha.cabeca_em(t) if self.trilha else (360, 400, 720, 1000)
            cr = a.caixa_ref
            y = cab[1] + 0.22 * (cab[3] - cab[1])
            opcoes = [(cab[2] + 10 - cr[0], y), (cab[0] - 10 - cr[2], y), ((cab[0] + cab[2]) / 2, cab[1] - 10 - cr[3])]
            outros = [c for c in (self.caixa_atual(b, t) for b in self.atores
                                  if b.ordem < a.ordem and b.caixa_ref and not b.zona.startswith("de:")) if c]
            for ox, oy in opcoes:
                caixa = (ox + cr[0], oy + cr[1], ox + cr[2], oy + cr[3])
                dentro = caixa[0] >= MARGEM and caixa[2] <= QW - MARGEM and caixa[1] >= SEGURA["topo"]
                if dentro and not any(_sobrepoe(caixa, c, FOLGA) for c in outros):
                    return ox, oy
            return opcoes[0] if opcoes[0][0] + cr[2] <= QW - MARGEM else opcoes[1]
        x, y = a.pos
        if not self._livre(a):
            return x, y
        dx, dy, k = self.ajuste(a, t)
        cr = a.caixa_grupo  # a reducao k e feita em volta do meio da caixa reservada
        mx, my = (cr[0] + cr[2]) / 2, (cr[1] + cr[3]) / 2
        return x + dx + mx * (1 - k), y + dy + my * (1 - k)

    @staticmethod
    def _encaixe(pai, a, rel, px, py):
        """Origem do filho grudado na caixa do pai: acima, abaixo, direita, esquerda ou dentro (centro)."""
        cr, fr = pai.caixa_ref, a.caixa_ref
        meio_x, meio_y = (cr[0] + cr[2]) / 2, (cr[1] + cr[3]) / 2
        if rel == "acima":
            return px + meio_x - (fr[0] + fr[2]) / 2, py + cr[1] - fr[3] - 10
        if rel == "abaixo":
            return px + meio_x - (fr[0] + fr[2]) / 2, py + cr[3] - fr[1] + 10
        if rel == "direita":
            return px + cr[2] - fr[0] + 14, py + meio_y - (fr[1] + fr[3]) / 2
        if rel == "esquerda":
            return px + cr[0] - fr[2] - 14, py + meio_y - (fr[1] + fr[3]) / 2
        return px + meio_x - (fr[0] + fr[2]) / 2, py + meio_y - (fr[1] + fr[3]) / 2

    def reducao(self, a, t):
        return self.ajuste(a, t)[2] if self._livre(a) else 1.0

    def posicao_final(self, a, t, e):
        x, y = self.posicao_base(a, t, e["params"])
        if e["orbita"]:
            t0, u = e["orbita"]
            grupo = [o for o in self.atores if any(an == "malabarismo" and abs(ta - t0) < 1e-6 for ta, an, _ in o.acoes)]
            cx = sum(self.posicao_base(o, t0, o.params)[0] for o in grupo) / len(grupo)
            cy = sum(self.posicao_base(o, t0, o.params)[1] for o in grupo) / len(grupo)
            cy = max(cy, ZONAS["topo_esquerdo"][3] + 150)  # malabarismo nunca sobe ate o contador
            rx, ry = 70, 45
            meia = max((o.caixa_ref[2] - o.caixa_ref[0]) / 2 for o in grupo) * 0.6
            meia_h = max((o.caixa_ref[3] - o.caixa_ref[1]) / 2 for o in grupo) * 0.6
            cab = self.trilha.cabeca_em(t) if self.trilha else None  # acompanha a cabeca (suave, janela de 0,6 s)
            if cab and _sobrepoe((cx - rx - meia, cy - ry - meia_h, cx + rx + meia, cy + ry + meia_h), cab):
                cx = cab[0] - rx - meia - FOLGA if cx < (cab[0] + cab[2]) / 2 else cab[2] + rx + meia + FOLGA
            cx = min(max(cx, rx + meia + MARGEM), QW - rx - meia - MARGEM)  # nem sai pela borda
            i = grupo.index(a)
            ang = 2 * math.pi * i / len(grupo) + 2 * math.pi * u / 1.4
            x, y = cx + rx * math.cos(ang), cy + ry * math.sin(ang)
        if e["voar"]:
            alvo_id, k = e["voar"]
            alvo = self.por_id[alvo_id]
            est_alvo = alvo.estado(t)
            if est_alvo:
                ax, ay = self.posicao_final(alvo, t, est_alvo)
                anc = ancoras(alvo.nome, **est_alvo["params"]).get("rotulo", (0, 0))
                ax, ay = ax + anc[0] * alvo.escala, ay + anc[1] * alvo.escala
                arco = -160 * math.sin(math.pi * k)
                x, y = x + (ax - x) * k, y + (ay - y) * k + arco
        return x + e["dx"], y + e["dy"]

    # ---------- desenho ----------
    def caixa_atual(self, a, t):
        e = a.estado(t)
        if not e or a.caixa_ref is None:
            return None
        x, y = self.posicao_final(a, t, e)
        k = self.reducao(a, t) * (1 - 0.45 * e["voar"][1] if e["voar"] else 1)
        kx, ky = k * e["sx"], k * e["sy"]  # inclui as escalas animadas (ex.: malabarismo encolhe)
        cr = a.caixa_ref
        return (x + cr[0] * kx, y + cr[1] * ky, x + cr[2] * kx, y + cr[3] * ky)

    def desenhar_atores(self, quadro, t):
        caixas = {}
        vivos = [(a, a.estado(t)) for a in self.atores]
        vivos = sorted(((a, e) for a, e in vivos if e), key=lambda ae: (ae[1]["voar"] is not None, ae[0].ordem))  # quem voa passa por cima
        for a, e in vivos:
            semente = T.fervura(t, a.ordem)
            if a.zona.startswith("de:"):
                self._desenhar_seta(quadro, a, t, e, semente)
                continue
            x, y = self.posicao_final(a, t, e)
            escala = a.escala * self.reducao(a, t)
            if e["voar"]:
                escala *= 1 - 0.45 * e["voar"][1]
            img, origem = obter(a.nome, escala=escala, semente=semente, progresso=round(e["progresso"], 2), **e["params"])
            caixa = colar(quadro, img, origem, x, y, e["sx"], e["sy"], e["rot"], e["opac"])
            if caixa:
                caixas[a.id] = caixa
            for tipo, frac in e["extras"]:
                if frac <= 0 or not caixa:
                    continue
                cx0, cy0, cx1, cy1 = caixa
                mx, my = (cx0 + cx1) / 2, (cy0 + cy1) / 2
                if tipo == "circulo":  # o circulo nao passa da borda do quadro
                    rx = min((cx1 - cx0) / 2 + 26, mx - 10, QW - 10 - mx)
                    ry = min((cy1 - cy0) / 2 + 22, my - SEGURA["topo"] + 20, QH - SEGURA["base"] - my)
                    im, org = obter("circulo", rx=round(max(40, rx) / 4) * 4, ry=round(max(40, ry) / 4) * 4, semente=semente, progresso=round(frac, 2))
                else:
                    meia = (cx1 - cx0) / 2 + 12
                    im, org = obter("linha", pontos=((-meia, 6), (meia, -6)), semente=semente, progresso=round(frac, 2))
                colar(quadro, im, org, mx, my)
        return caixas

    def _desenhar_seta(self, quadro, a, t, e, semente):
        de, para = a.zona[3:].split(">para:")
        ca = self.caixa_atual(self.por_id[de], t)
        if para.startswith("@"):  # um ponto fixo da tela (ex.: o nome do perfil no Reels)
            px, py = (float(v) for v in para[1:].split(","))
            cb = (px, py, px, py + 18)
        else:
            cb = self.caixa_atual(self.por_id[para], t)
        if not ca or not cb:
            return
        o = ((ca[0] + ca[2]) / 2, ca[3] + 14)
        d = ((cb[0] + cb[2]) / 2, cb[1] - 18)
        # a curva da seta vai para o lado oposto a cabeca
        cab = self.trilha.cabeca_em(t) if self.trilha else None
        curva = -0.3
        if cab:
            meio = ((o[0] + d[0]) / 2, (o[1] + d[1]) / 2)
            normal = (-(d[1] - o[1]), d[0] - o[0])
            centro = ((cab[0] + cab[2]) / 2, (cab[1] + cab[3]) / 2)
            lado = (meio[0] - centro[0]) * normal[0] + (meio[1] - centro[1]) * normal[1]
            curva = 0.3 if lado > 0 else -0.3
        arred = lambda v: round(v / 6) * 6
        im, org = obter("seta", origem=(arred(o[0]), arred(o[1])), destino=(arred(d[0]), arred(d[1])), curva=curva,
                        semente=semente, progresso=round(e["progresso"], 2))
        colar(quadro, im, org, 0, 0, opacidade=e["opac"])

    # ---------- camera e som ----------
    def camera(self, t):
        """(zoom, dx, dy) somando os impactos ativos: zoom com mola que nunca fica abaixo de 1 + tremida."""
        z, dx, dy = 1.0, 0.0, 0.0
        cfg_z, cfg_t = IMPACTO["zoom"], IMPACTO["tremida_tela"]
        for ti in self.impactos:
            u = t - ti
            if 0 <= u < 1.2:
                z += cfg_z["amplitude"] * math.exp(-cfg_z["amortecimento"] * u) * (math.cos(cfg_z["frequencia"] * u) + 1) / 2
                ox, oy = T.tremida(t, ti, cfg_t["duracao"], cfg_t["amplitude_px"], cfg_t["fps"], semente=int(ti * 100))
                dx, dy = dx + ox, dy + oy
        folga = (z - 1) * QW / 2
        return z, max(-folga, min(folga, dx)), max(-folga, min(folga, dy))

    def cena_em(self, t):
        for c in self.cenas:
            if c.inicio <= t < c.fim:
                return c
        return self.cenas[-1]
