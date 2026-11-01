"""Revisao automatica antes de mostrar: confere o video inteiro quadro a quadro, sem renderizar.

Regras: nada cortado nas bordas; legenda nunca coberta; areas seguras do Reels livres; desenhos sem
sobreposicao acidental; rosto livre; texto legivel no celular; fala e animacao sincronizadas.
"""
from collections import defaultdict

import numpy as np

from motor.cenas import BOTOES_REELS, _sobrepoe
from motor.estilo import ESTILO
from motor.legenda import _diagramar, limpar
from motor.render import ler_quadros

QW, QH = ESTILO["quadro"]["largura"], ESTILO["quadro"]["altura"]
SEG = ESTILO["areas_seguras"]
CX, CY = ESTILO["legenda"]["caixa"]["centro"]
LW, LH = ESTILO["legenda"]["caixa"]["largura"], ESTILO["legenda"]["caixa"]["altura"]
CAIXA_LEGENDA = (CX - LW / 2 - 10, CY - LH / 2 - 12, CX + LW / 2 + 10, CY + LH / 2 + 12)
TOPO_RUIM = (0, 0, QW, SEG["topo"])
BASE_RUIM = (0, QH - SEG["base"], QW, QH)
LETRA_MINIMA = 36  # px num quadro de 1080: ~13 pt na tela do celular
SAIDAS_DE_PROPOSITO = {"voar_longe", "despencar"}
TAMANHO_TEXTO = {"texto_mao": 64, "contador": 56, "etiqueta_preco": 44, "relogio_ponto": 42, "cracha": 60,
                 "selo": 46, "balanca": 52, "transferidor": 44}


def _tamanho_texto(a):
    """Tamanho real da letra (na escala 1) do texto principal do desenho."""
    if a.nome == "selo":  # o selo reduz a letra ate o texto caber
        from motor.estilo import fonte
        tam, texto = 54, a.params.get("texto", "")
        while tam > 18 and fonte("titulo", tam).getlength(texto) > 286:
            tam -= 2
        return tam
    return a.params.get("tamanho", TAMANHO_TEXTO[a.nome])


def _ancestrais(a):
    out = set()
    if ":" in a.zona and not a.zona.startswith("de:"):
        out.add(a.zona.split(":", 1)[1])  # encaixado em outro (ex.: dentro do cartao)
    while a.pai:
        a = a.pai[0]
        out.add(a.id)
    return out


ENTRADAS_COM_QUIQUE = {"pop", "colar", "borrifar", "procurar", "balancar", "balancar_e_circular", "acender"}
IMPULSOS = {"bater", "apertar", "receber_selo", "virar_pao_frances", "flexionar", "crescer", "pingar", "boina",
            "marcar_concluido", "multiplicar", "gritar"}


def _saindo_de_proposito(a, t):
    """Movimentos que cruzam a tela de proposito: cair/fincar/subir na entrada, saida, voar ou despencar,
    e o quique passageiro (ate 0,3 s) das entradas e dos impactos."""
    if a.anim_entra in ("cair", "fincar", "subir") and t - a.t_entra < 0.45:
        return True
    if a.anim_entra in ENTRADAS_COM_QUIQUE and t - a.t_entra < 0.3:
        return True
    if any(anim in IMPULSOS and 0 <= t - ta < 0.3 for ta, anim, _ in a.acoes):
        return True
    if a.t_sai is not None and t >= a.t_sai:
        return True
    return any(t >= ta and anim in SAIDAS_DE_PROPOSITO for ta, anim, _ in a.acoes)


def _rosto(cabeca):
    """Tira da caixa da cabeca as margens de seguranca (testa/cabelo) e volta ao rosto em si."""
    m = ESTILO["rosto"]
    x0, y0, x1, y1 = cabeca
    w = (x1 - x0) / (1 + 2 * m["margem_lado"])
    h = (y1 - y0) / (1 + m["margem_topo"] + m["margem_baixo"])
    return x0 + w * m["margem_lado"], y0 + h * m["margem_topo"], x1 - w * m["margem_lado"], y1 - h * m["margem_baixo"]


def _malabarismo(a, t):
    return any(t >= ta and anim == "malabarismo" for ta, anim, _ in a.acoes)


def revisar_layout(motor, fps=15):
    f = motor.filme
    from motor.legenda import caixa_ocupada
    x0, y0, x1, y1 = caixa_ocupada(motor.roteiro.get("opcoes", {}))
    CAIXA_LEGENDA = (x0 - 10, y0 - 12, x1 + 10, y1 + 12)
    problemas = defaultdict(list)  # (regra, detalhe) -> instantes
    seta = lambda a: a.zona.startswith("de:")
    n = int((motor.fim - motor.inicio) * fps)
    for i in range(n):
        t = round(motor.inicio + i / fps, 3)
        if any(tr["inicio"] <= t <= tr["fim"] for tr in f.transicoes):
            continue  # o rabisco cobre tudo
        cab = f.trilha.cabeca_em(t) if f.trilha else None
        caixas = {}
        for a in f.atores:
            if seta(a) or a.caixa_ref is None:
                continue
            c = f.caixa_atual(a, t)
            if c:
                caixas[a.id] = (a, c)
        for aid, (a, c) in caixas.items():
            livre_de_regra = _saindo_de_proposito(a, t) or any(t >= ta and an.startswith("voar_e_colar") for ta, an, _ in a.acoes)
            cobre_texto_antigo = "cobrir" in a.el or a.fixo  # tem lugar fixo: em cima do titulo antigo
            if not livre_de_regra and (c[0] < 0 or c[1] < 0 or c[2] > QW or c[3] > QH):
                problemas[("cortado na borda", aid)].append(t)
            if not livre_de_regra and _sobrepoe(c, CAIXA_LEGENDA) and a.zona != "abaixo_legenda":
                problemas[("encosta na legenda", aid)].append(t)
            if not livre_de_regra and a.zona == "abaixo_legenda" and c[1] < CAIXA_LEGENDA[3] - 1:
                problemas[("encosta na legenda", aid)].append(t)
            for nome, area in (("area do topo do Reels", TOPO_RUIM), ("area da base do Reels", BASE_RUIM), ("botoes do Reels", BOTOES_REELS)):
                if not livre_de_regra and _sobrepoe(c, area):
                    problemas[(nome, aid)].append(t)
            # o layout ja foge da cabeca inteira (com margem); aqui so e problema encostar no rosto
            if cab and _sobrepoe(c, _rosto(cab)) and not livre_de_regra and not cobre_texto_antigo:
                problemas[("encosta no rosto", aid)].append(t)
        ids = list(caixas)
        for x in range(len(ids)):
            for y in range(x + 1, len(ids)):
                (a, ca), (b, cb) = caixas[ids[x]], caixas[ids[y]]
                if a.id in _ancestrais(b) or b.id in _ancestrais(a):
                    continue
                voando = any(an.startswith("voar_e_colar") for _, an, _ in a.acoes + b.acoes)
                if voando or _saindo_de_proposito(a, t) or _saindo_de_proposito(b, t):
                    continue
                if _malabarismo(a, t) and _malabarismo(b, t):
                    continue  # malabarismo: um passa pelo outro de proposito
                if _sobrepoe(ca, cb, -6):
                    problemas[("desenhos sobrepostos", f"{a.id} × {b.id}")].append(t)
    return problemas


def revisar_leitura(motor):
    f, avisos = motor.filme, []
    for a in f.atores:
        if a.nome not in TAMANHO_TEXTO or not (a.params.get("texto") or a.params.get("rotulo")):
            continue
        tam = _tamanho_texto(a) * a.escala
        if tam < LETRA_MINIMA:
            avisos.append(f"{a.id}: texto “{a.params.get('texto') or a.params.get('rotulo')}” com {tam:.0f}px (minimo {LETRA_MINIMA})")
    menor = min(_diagramar(tuple(limpar(p["texto"]) for p in b["palavras"]))[0] for b in motor.legenda.blocos)
    return avisos, menor


def revisar_sincronia(motor):
    """Cada gatilho comeca no inicio da palavra (+ atraso combinado); o quadro arredonda no maximo 1/30 s."""
    maior_atraso, fora = 0.0, []
    for a in motor.filme.atores:
        for g in [a.el["entra"]] + a.el.get("acoes", []) + ([a.el["sai"]] if "sai" in a.el else []):
            atraso = g.get("atraso", 0.0)
            maior_atraso = max(maior_atraso, atraso)
            if atraso > 0.9:
                fora.append(f"{a.id}: {atraso:.2f}s depois da palavra")
    return maior_atraso, fora


def revisar_pixels(motor, fps=2):
    """Procura a legenda/titulo antigos vazando: os pixels brancos do texto no video bruto
    precisam estar cobertos no quadro final (la eles nao podem continuar brancos)."""
    vazamentos = []
    if not motor.tem_video:
        return vazamentos
    opcoes = motor.roteiro.get("opcoes", {})
    tit_ate = opcoes.get("cobrir_titulo_antigo_ate", 0)
    regioes = []
    if opcoes.get("cobrir_legenda_antiga"):
        regioes.append(("legenda antiga", (slice(1100, 1420), slice(100, 980)), None))
    if tit_ate:
        regioes.append(("titulo antigo", (slice(244, 420), slice(274, 800)), tit_ate))
    for n, fundo in enumerate(ler_quadros(motor.video, motor.inicio, motor.fim - motor.inicio, fps=fps)):
        t = motor.inicio + n / fps
        if any(tr["inicio"] <= t <= tr["fim"] for tr in motor.filme.transicoes):
            continue
        bruto = np.asarray(fundo)
        final = np.asarray(motor.quadro(fundo, t).convert("RGB"))
        for nome, reg, ate in regioes:
            if ate is not None and t >= ate:
                continue
            texto_antigo = (bruto[reg] > 248).all(axis=2)
            ainda_branco = texto_antigo & (final[reg] > 246).all(axis=2)
            if ainda_branco.sum() > 25:
                vazamentos.append((round(t, 2), nome, int(ainda_branco.sum())))
    return vazamentos


def agrupar(instantes, passo=0.1):
    """[1.0, 1.07, 1.13, 5.2] -> ['1.00–1.13s', '5.20s']"""
    faixas, ini, ant = [], None, None
    for t in sorted(instantes):
        if ini is None:
            ini = ant = t
        elif t - ant > passo + 1e-6:
            faixas.append((ini, ant))
            ini = t
        ant = t
    if ini is not None:
        faixas.append((ini, ant))
    return [f"{a:.2f}s" if a == b else f"{a:.2f}–{b:.2f}s" for a, b in faixas]
