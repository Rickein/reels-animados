"""Roteiro de cenas: carrega, valida as regras e gera a tabela legivel para aprovacao."""
import json
import re
from pathlib import Path

from motor.ambiente import RAIZ

DUR_MIN, DUR_MAX = 2.0, 4.0     # duracao de cada cena (s)
PARADO_MAX = 1.0                # nada de tela parada por mais que isso (s)
ELEMENTOS_SEM_NOVIDADE = 1.6    # aviso se os desenhos ficam esse tempo sem nenhuma acao (s)
ZONA_LOTADA = 3                 # elementos visiveis ao mesmo tempo na mesma zona


def _norm(s: str) -> str:
    return re.sub(r"[^\w]", "", s.lower())


def carregar(trabalho: str):
    """Roteiro ja com as cenas modelo transformadas em elementos."""
    from motor.modelos import expandir
    pasta = RAIZ / "trabalhos" / trabalho
    roteiro = json.loads((pasta / "roteiro.json").read_text(encoding="utf-8"))
    palavras = json.loads((pasta / "palavras.json").read_text(encoding="utf-8"))["palavras"]
    estilo = json.loads((RAIZ / "estilo.json").read_text(encoding="utf-8"))
    return pasta, expandir(roteiro, palavras), palavras, estilo


def gatilhos(roteiro):
    """Todos os gatilhos (entra / acao / sai) como dicionarios planos, na ordem do roteiro."""
    for el in roteiro["elementos"]:
        partes = [("entra", el["entra"])] + [("acao", a) for a in el.get("acoes", [])]
        if "sai" in el:
            partes.append(("sai", el["sai"]))
        for tipo, g in partes:
            yield {"elemento": el["id"], "desenho": el["desenho"], "tipo": tipo, "em": g["em"],
                   "palavra": g.get("palavra"), "anim": g["anim"], "atraso": g.get("atraso", 0.0),
                   "impacto": g.get("impacto", False)}


def tempo_gatilho(palavras, g) -> float:
    return round(palavras[g["em"]]["inicio"] + g.get("atraso", 0.0), 3)


def transicoes(roteiro, palavras, duracao):
    """Transicao antes de cada capitulo (menos o primeiro): centrada na pausa, ou logo apos a ultima palavra.
    Com "opcoes": {"transicoes": [1]} so esses capitulos tem rabisco; nos outros fica um corte seco
    (duracao zero, no corte do take quando "numeros_atras" diz onde e), que so limpa os desenhos."""
    opcoes = roteiro.get("opcoes", {})
    com_rabisco = opcoes.get("transicoes")
    cortes = {item["n"]: item["t"] for item in opcoes.get("numeros_atras", [])}
    lista = []
    for cap in roteiro["capitulos"][1:]:
        s = cap["palavra_inicio"]
        fim_ant, ini_prox = palavras[s - 1]["fim"], palavras[s]["inicio"]
        pausa = ini_prox - fim_ant
        if com_rabisco is not None and cap["n"] not in com_rabisco:
            t = cortes.get(cap["n"], fim_ant + pausa / 2)
            lista.append({"capitulo": cap["n"], "inicio": round(t, 3), "fim": round(t, 3), "corte": True})
            continue
        ini = fim_ant + (pausa - duracao) / 2 if pausa >= duracao else fim_ant - 0.05
        lista.append({"capitulo": cap["n"], "inicio": round(ini, 3), "fim": round(ini + duracao, 3)})
    return lista


def tempos_das_cenas(roteiro, palavras):
    cenas = roteiro["cenas"]
    out = []
    for k, c in enumerate(cenas):
        ini = palavras[c["palavras"][0]]["inicio"] if k else roteiro["inicio"]
        fim = palavras[cenas[k + 1]["palavras"][0]]["inicio"] if k + 1 < len(cenas) else roteiro["fim"]
        out.append((round(ini, 3), round(fim, 3)))
    return out


def vida_dos_elementos(roteiro, palavras, trans):
    """Intervalo em que cada elemento esta na tela. Sem 'sai', some na transicao seguinte (ou no fim)."""
    vida = {}
    for el in roteiro["elementos"]:
        ini = tempo_gatilho(palavras, {"em": el["entra"]["em"], "atraso": el["entra"].get("atraso", 0.0)})
        if "sai" in el:
            fim = tempo_gatilho(palavras, {"em": el["sai"]["em"], "atraso": el["sai"].get("atraso", 0.0)}) + 0.25
        else:
            depois = [t for t in trans if t["inicio"] > ini]
            fim = (depois[0]["inicio"] + depois[0]["fim"]) / 2 if depois else roteiro["fim"]
        vida[el["id"]] = (ini, round(fim, 3))
    return vida


def validar(roteiro, palavras, estilo):
    erros, avisos = [], []
    n = len(palavras)
    trans = transicoes(roteiro, palavras, estilo["transicao"]["duracao"])
    gs = list(gatilhos(roteiro))

    # 1. cada gatilho aponta para a palavra certa
    for g in gs:
        if not 0 <= g["em"] < n:
            erros.append(f"{g['elemento']}: palavra {g['em']} nao existe")
        elif g["palavra"] and _norm(g["palavra"]) != _norm(palavras[g["em"]]["texto"]):
            erros.append(f"{g['elemento']}: esperava “{g['palavra']}” na palavra {g['em']}, mas e “{palavras[g['em']]['texto']}”")

    # 2. ordem dentro de cada elemento: entra -> acoes -> sai
    for el in roteiro["elementos"]:
        ts = [tempo_gatilho(palavras, g) for g in gs if g["elemento"] == el["id"]]
        if ts != sorted(ts):
            erros.append(f"{el['id']}: gatilhos fora de ordem")

    # 3. cenas cobrem todas as palavras, na ordem, com 2 a 4 s e um unico impacto (na palavra-chave)
    esperado = 0
    for c, (ini, fim) in zip(roteiro["cenas"], tempos_das_cenas(roteiro, palavras)):
        a, b = c["palavras"]
        if a != esperado:
            erros.append(f"{c['id']}: comeca na palavra {a}, esperava {esperado}")
        esperado = b + 1
        dur = fim - ini
        if not DUR_MIN - 0.25 <= dur <= DUR_MAX + 0.6:
            avisos.append(f"{c['id']}: dura {dur:.2f}s (alvo 2–4s)")
        impactos = [g for g in gs if g["impacto"] and a <= g["em"] <= b]
        if len(impactos) != 1:
            erros.append(f"{c['id']}: tem {len(impactos)} impactos (precisa de exatamente 1)")
        elif impactos[0]["em"] != c["chave"]:
            erros.append(f"{c['id']}: impacto na palavra {impactos[0]['em']}, mas a chave e {c['chave']}")
    if esperado != n:
        erros.append(f"as cenas terminam na palavra {esperado - 1}, mas a fala vai ate {n - 1}")

    # 4. tela nunca parada: legenda (cada palavra), desenhos e transicoes
    ev_desenhos = sorted({tempo_gatilho(palavras, g) for g in gs} | {t[k] for t in trans for k in ("inicio", "fim")})
    ev_todos = sorted(set(ev_desenhos) | {p["inicio"] for p in palavras} | {roteiro["inicio"], roteiro["fim"]})
    maior = max(zip(ev_todos, ev_todos[1:]), key=lambda x: x[1] - x[0])
    if maior[1] - maior[0] > PARADO_MAX:
        erros.append(f"tela parada por {maior[1] - maior[0]:.2f}s entre {maior[0]:.2f}s e {maior[1]:.2f}s")
    ev_d = sorted(set(ev_desenhos) | {roteiro["inicio"], roteiro["fim"]})
    for x, y in zip(ev_d, ev_d[1:]):
        if y - x > ELEMENTOS_SEM_NOVIDADE:
            avisos.append(f"desenhos sem novidade por {y - x:.2f}s ({x:.2f}s → {y:.2f}s)")

    # 5. zonas lotadas
    vida = vida_dos_elementos(roteiro, palavras, trans)
    zona_de = {el["id"]: el["zona"] for el in roteiro["elementos"]}
    for t in ev_d:
        por_zona = {}
        for eid, (ini, fim) in vida.items():
            z = zona_de[eid]
            if ini <= t < fim and ":" not in z:
                por_zona.setdefault(z, []).append(eid)
        for z, ids in por_zona.items():
            if len(ids) > ZONA_LOTADA:
                avisos.append(f"{t:.2f}s: {len(ids)} elementos em {z} ({', '.join(ids)})")

    return erros, sorted(set(avisos)), {"transicoes": trans, "maior_parada": round(maior[1] - maior[0], 2)}


def _nome(s: str) -> str:
    return s.replace("_", " ")


def tabela_md(roteiro, palavras, estilo) -> str:
    gs = list(gatilhos(roteiro))
    caps = {c["n"]: c for c in roteiro["capitulos"]}
    inicio_cap = {c["palavra_inicio"]: c["n"] for c in roteiro["capitulos"]}
    trans = {t["capitulo"]: t for t in transicoes(roteiro, palavras, estilo["transicao"]["duracao"])}
    linhas = ["| Cena | Tempo | Frase | Metáfora visual | Elementos | Palavra → animação |",
              "|---|---|---|---|---|---|"]
    cap_atual = None
    for c, (ini, fim) in zip(roteiro["cenas"], tempos_das_cenas(roteiro, palavras)):
        a, b = c["palavras"]
        cap = max(n for p, n in inicio_cap.items() if p <= a)
        if cap != cap_atual:
            cap_atual = cap
            extra = f" · transição rabisco {trans[cap]['inicio']:.2f}–{trans[cap]['fim']:.2f}s" if cap in trans else ""
            linhas.append(f"| **{caps[cap]['nome'].upper()}**{extra} | | | | | |")
        frase = " ".join(p["texto"] for p in palavras[a:b + 1])
        novos = [g for g in gs if g["tipo"] == "entra" and a <= g["em"] <= b]
        elementos = ", ".join(dict.fromkeys(_nome(g["desenho"]) for g in novos)) or "—"
        disparos = []
        for g in sorted((g for g in gs if a <= g["em"] <= b), key=lambda g: tempo_gatilho(palavras, g)):
            palavra = palavras[g["em"]]["texto"].strip(".,")
            item = f"“{palavra}” → {_nome(g['anim'])} ({_nome(g['desenho'])})"
            disparos.append(f"**⚡ {item}**" if g["impacto"] else item)
        linhas.append(f"| {c['id']} | {ini:05.2f}–{fim:05.2f} | {frase} | {c['metafora']} | {elementos} | {'<br>'.join(disparos)} |")
    return "\n".join(linhas) + "\n"
