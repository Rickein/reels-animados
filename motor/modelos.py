"""Cenas modelo: estruturas prontas que viram desenhos comuns do roteiro.

No roteiro.json, uma cena pode ter  "modelo": {"tipo": ..., ...}. Ao carregar o roteiro, o modelo vira
elementos normais (ids "<cena>_..."), entao validador, revisao e motor tratam tudo do mesmo jeito.

Tipos e parametros ("em" = indice da palavra no palavras.json):
  lista               itens: [{em, texto, marcar_em?}], zona?
  passo_a_passo       passos: [{em, texto}], zona?
  numero_grande       em, numero, rotulo?, zona?
  comparacao          esquerda: {em, texto | desenho}, direita: {...}, veredito?: {em, vencedor: esquerda|direita}, zona?
  antes_depois        antes: {em, texto | desenho}, depois: {...}, zona?  (sem zona: as laterais do rosto)
  chamada_para_seguir em, texto, zona?
"""
import copy

TIPOS = ("lista", "passo_a_passo", "numero_grande", "comparacao", "antes_depois", "chamada_para_seguir")


def _g(palavras, em, anim, impacto=False, atraso=0.0):
    g = {"em": em, "palavra": palavras[em]["texto"], "anim": anim}
    if impacto:
        g["impacto"] = True
    if atraso:
        g["atraso"] = atraso
    return g


def _conteudo(pid, lado, palavras, zona, impacto=False, slot=None):
    """Um lado de comparacao/antes-depois: um desenho da biblioteca ou um texto escrito a mao."""
    if lado.get("desenho"):
        el = {"id": pid, "desenho": lado["desenho"], "zona": zona, "entra": _g(palavras, lado["em"], "pop", impacto)}
        el.update({k: v for k, v in lado.items() if k not in ("em", "desenho")})
    else:
        el = {"id": pid, "desenho": "texto_mao", "texto": lado.get("texto", palavras[lado["em"]]["texto"]), "zona": zona,
              "entra": _g(palavras, lado["em"], "escrever", impacto)}
    if slot:
        el["slot"] = slot
    return el


def _dois_lados(m):
    """Zonas dos dois lados: as laterais do rosto (padrao) ou as duas metades de uma zona (ex.: palco)."""
    if m.get("zona"):
        return (m["zona"], [0, 2]), (m["zona"], [1, 2])
    return ("lado_esquerdo", None), ("lado_direito", None)


def lista(cid, m, palavras, numerada=False):
    itens = m.get("passos" if numerada else "itens", [])
    zona = m.get("zona", "lado_direito")
    els = []
    for k, it in enumerate(itens):
        el = {"id": f"{cid}_{'passo' if numerada else 'item'}{k + 1}", "desenho": "item_lista", "texto": it["texto"],
              "zona": zona, "slot": [k, len(itens)], "entra": _g(palavras, it["em"], "escrever", k == len(itens) - 1)}
        if numerada:
            el["numero"] = k + 1
        if it.get("marcar_em") is not None:
            el["acoes"] = [_g(palavras, it["marcar_em"], "marcar")]
        els.append(el)
    return els


def numero_grande(cid, m, palavras):
    els = [{"id": f"{cid}_numero", "desenho": "texto_mao", "texto": str(m["numero"]), "tamanho": 170,
            "zona": m.get("zona", "topo_direito"), "entra": _g(palavras, m["em"], "contar_numero", True)}]
    if m.get("rotulo"):
        els.append({"id": f"{cid}_rotulo", "desenho": "texto_mao", "texto": m["rotulo"], "tamanho": 52,
                    "zona": f"abaixo:{cid}_numero", "entra": _g(palavras, m["em"], "escrever", atraso=0.35)})
    return els


def comparacao(cid, m, palavras):
    (ze, se), (zd, sd) = _dois_lados(m)
    esq = _conteudo(f"{cid}_esquerda", m["esquerda"], palavras, ze, slot=se)
    tem_veredito = "veredito" in m
    dir_ = _conteudo(f"{cid}_direita", m["direita"], palavras, zd, impacto=not tem_veredito, slot=sd)
    els = [esq, dir_, {"id": f"{cid}_vs", "desenho": "texto_mao", "texto": "vs", "tamanho": 90, "zona": "topo_centro",
                       "entra": _g(palavras, m["direita"]["em"], "pop")}]
    if tem_veredito:
        v = m["veredito"]
        ganhou = esq["id"] if v.get("vencedor", "esquerda") == "esquerda" else dir_["id"]
        perdeu = dir_["id"] if ganhou == esq["id"] else esq["id"]
        els += [{"id": f"{cid}_certo", "desenho": "check", "zona": f"acima:{ganhou}", "entra": _g(palavras, v["em"], "pop", True)},
                {"id": f"{cid}_errado", "desenho": "xis", "zona": f"acima:{perdeu}", "entra": _g(palavras, v["em"], "pop")}]
    return els


def antes_depois(cid, m, palavras):
    (za, sa), (zd, sd) = _dois_lados(m)
    a = _conteudo(f"{cid}_antes", m["antes"], palavras, za, slot=sa)
    d = _conteudo(f"{cid}_depois", m["depois"], palavras, zd, impacto=True, slot=sd)
    return [a, d,
            {"id": f"{cid}_rotulo_antes", "desenho": "texto_mao", "texto": "antes", "tamanho": 46, "zona": f"acima:{a['id']}",
             "entra": _g(palavras, m["antes"]["em"], "escrever")},
            {"id": f"{cid}_rotulo_depois", "desenho": "texto_mao", "texto": "depois", "tamanho": 46, "zona": f"acima:{d['id']}",
             "entra": _g(palavras, m["depois"]["em"], "escrever")},
            {"id": f"{cid}_seta", "desenho": "seta_curva", "zona": f"de:{a['id']}>para:{d['id']}",
             "entra": _g(palavras, m["depois"]["em"], "desenhar")}]


def chamada_para_seguir(cid, m, palavras):
    """Fim do video: texto escrito, coracao pulsando e uma seta apontando para o nome do perfil no Reels."""
    zona = m.get("zona", "abaixo_legenda")
    return [{"id": f"{cid}_chamada", "desenho": "texto_mao", "texto": m.get("texto", "me segue pra mais!"), "tamanho": 64,
             "zona": zona, "entra": _g(palavras, m["em"], "escrever", m.get("impacto", False))},
            {"id": f"{cid}_coracao", "desenho": "coracao", "zona": f"direita:{cid}_chamada", "escala": 0.8,
             "entra": _g(palavras, m["em"], "pop", atraso=0.5), "acoes": [_g(palavras, m["em"], "pulsar", atraso=0.8)]},
            {"id": f"{cid}_seta", "desenho": "seta_curva", "zona": f"de:{cid}_chamada>para:@170,1640",
             "entra": _g(palavras, m["em"], "desenhar", atraso=0.6)}]


def expandir(roteiro, palavras):
    """Copia do roteiro com os modelos das cenas transformados em elementos (e a chave preenchida)."""
    r = copy.deepcopy(roteiro)
    for cena in r["cenas"]:
        m = cena.get("modelo")
        if not m:
            continue
        tipo, cid = m["tipo"], cena["id"]
        if tipo == "lista":
            novos = lista(cid, m, palavras)
        elif tipo == "passo_a_passo":
            novos = lista(cid, m, palavras, numerada=True)
        elif tipo == "numero_grande":
            novos = numero_grande(cid, m, palavras)
        elif tipo == "comparacao":
            novos = comparacao(cid, m, palavras)
        elif tipo == "antes_depois":
            novos = antes_depois(cid, m, palavras)
        elif tipo == "chamada_para_seguir":
            novos = chamada_para_seguir(cid, m, palavras)
        else:
            raise ValueError(f"{cid}: modelo desconhecido '{tipo}' (use um de: {', '.join(TIPOS)})")
        if m.get("sai_em") is not None:  # todos os desenhos do modelo saem juntos nessa palavra
            for el in novos:
                el.setdefault("sai", _g(palavras, m["sai_em"], "borracha"))
        r["elementos"] += novos
        if "chave" not in cena:
            imp = [g["em"] for el in novos for g in [el["entra"]] + el.get("acoes", []) if g.get("impacto")]
            if imp:
                cena["chave"] = imp[0]
    return r
