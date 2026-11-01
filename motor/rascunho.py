"""Rascunho automatico do roteiro: divide a fala em capitulos e cenas, escolhe a palavra-chave de cada
cena, procura um desenho da biblioteca que combine e reconhece padroes que viram cenas modelo
(numero grande, lista, passo a passo, antes e depois).

E so um ponto de partida: a pessoa revisa o roteiro.md e muda o roteiro.json antes de renderizar.
"""
import re
import unicodedata

PONTUACAO = ".!?…"
PAUSA_CENA = 0.25       # pausa que permite cortar cena (s)
PAUSA_CAPITULO = 0.6    # pausa que permite trocar de capitulo (s)
CENA_MIN, CENA_MAX = 2.0, 3.6
CAPITULO_MIN, CAPITULO_MAX = 6.0, 14.0

STOP = set("""a o as os um uma uns umas de da do das dos em no na nos nas por pra pro pras pros para com sem que e
e ou mas se ser sao foi era ta esta estao estar eu voce voces ele ela eles elas nos me te lhe isso isto esse essa
este esta aquilo aquele aquela muito muita mais menos ja nao sim tem tem ter tinha vai vao vou so tambem quando onde
como porque porque qual quais quem tudo nada todo toda todos todas ao aos as ate meu minha seu sua dele dela num numa
la aqui ali entao assim bem tipo coisa coisas gente ai ne pois olha cara vez vezes fazer faz fez sabe acho""".split())

# (raizes da palavra, desenho, parametros)
DICIONARIO = [
    (("celular", "instagram", "insta", "tiktok", "feed", "story", "stories", "post", "reels", "rede", "online", "app", "foto"), "celular", {}),
    (("internet", "wifi", "site", "google"), "wifi", {}),
    (("coracao", "amor", "saude", "saudavel", "curtid", "like", "cuidar", "carinho"), "coracao", {}),
    (("dinheiro", "reais", "caro", "barato", "preco", "pagar", "pago", "gasta", "lucro", "grana", "vende", "vend"), "cifroes", {}),
    (("casa", "lar", "familia"), "casa", {}),
    (("grafico", "resultado", "cresc", "aument", "meta", "evolu", "progress"), "grafico", {}),
    (("medo", "ansiedad", "ansios", "desesper", "nervos", "panico", "suor", "estress", "pressao"), "gotas_suor", {}),
    (("pao", "carbo", "massa", "trigo", "gluten", "arroz", "macarrao"), "pao", {}),
    (("treino", "academia", "musculacao", "halter", "malh", "exercici", "peso", "forca"), "halter", {}),
    (("corrida", "correr", "caminha", "tenis", "cardio"), "tenis", {}),
    (("yoga", "pilates", "alonga"), "tapete_yoga", {}),
    (("agua", "hidrat", "beber", "garrafa"), "garrafa_agua", {}),
    (("praia", "verao", "ferias", "biquini"), "guarda_sol", {}),
    (("sol", "calor", "manha"), "sol", {}),
    (("espelho", "aparenc", "reflexo", "vaidade"), "espelho", {}),
    (("balanca", "equilibr", "pesar"), "balanca", {"texto": ""}),
    (("relogio", "hora", "horario", "tempo", "rotina", "agenda", "atrasad"), "relogio_ponto", {"texto": ""}),
    (("minuto", "segundo", "rapid", "cronomet"), "cronometro", {}),
    (("trabalh", "emprego", "clt", "chefe", "escritorio", "carreira"), "cracha", {"texto": "CLT"}),
    (("ideia", "descobr", "sacada", "solucao", "aprend", "entend"), "lampada", {}),
    (("industria", "empresa", "marca", "fabrica", "produto"), "fabrica", {}),
    (("compr", "mercado", "shopping", "sacola", "loja"), "sacola", {}),
    (("proteina", "proteic", "whey", "suplement"), "selo", {"texto": "+PROTEÍNA"}),
    (("salada", "dieta", "comida", "prato", "refeic", "aliment", "comer", "almoco", "jantar"), "prato_salada", {}),
    (("pens", "acha", "acham", "acredit", "sonh", "imagin"), "balao_pensamento", {}),
    (("fala", "dizer", "conversa", "conta", "perguntar"), "balao_fala", {}),
    (("busca", "procur", "encontr", "detalhe", "investig"), "lupa", {}),
    (("forte", "musculo", "definid", "definicao"), "biceps", {}),
    (("ver", "olhar", "observ", "enxerg"), "binoculos", {}),
    (("angulo", "filtro", "edicao", "editad"), "transferidor", {}),
    (("limp", "detox"), "borrifador", {}),
    (("influenc", "blogueir", "famos"), "ring_light", {}),
    (("lista", "tarefa", "obrigac"), "lista_tarefas", {}),
    (("megafone", "grita", "anunci", "convenc", "propaganda", "publicidade"), "megafone", {}),
    (("medida", "cintura", "centimetro", "magreza", "magra", "magro", "emagrec", "engord"), "fita_metrica", {}),
    (("mentira", "mito", "errad", "falso"), "xis", {}),
    (("verdade", "certo", "correto"), "check", {}),
]
NUMEROS = {"dois": 2, "duas": 2, "tres": 3, "quatro": 4, "cinco": 5, "seis": 6, "sete": 7, "oito": 8, "nove": 9,
           "dez": 10, "quinze": 15, "vinte": 20, "trinta": 30, "quarenta": 40, "cinquenta": 50, "cem": 100, "mil": 1000}
ORDINAIS = {"primeiro": 1, "primeira": 1, "segundo": 2, "segunda": 2, "terceiro": 3, "terceira": 3, "quarto": 4, "quarta": 4, "quinto": 5}
ANIMACAO_DE_ENTRADA = {"texto_mao": "escrever", "seta_subindo": "desenhar", "wifi": "desenhar", "lista_tarefas": "desenrolar",
                       "lampada": "acender", "lupa": "procurar", "binoculos": "procurar", "guarda_sol": "fincar",
                       "sacola": "cair", "halter": "cair", "borrifador": "borrifar", "cifroes": "subir"}
ACAO_DE_IMPACTO = {"megafone": "gritar", "balanca": "tombar", "biceps": "brilhar", "pao": "circular", "fita_metrica": "espiral",
                   "espelho": "espremer_reflexo", "lista_tarefas": "desenrolar_longo", "transferidor": "medir_angulo"}


def normal(w):
    s = unicodedata.normalize("NFD", w.lower())
    return re.sub(r"[^\w]", "", "".join(c for c in s if unicodedata.category(c) != "Mn"))


def desenho_para(palavra):
    p = normal(palavra)
    if len(p) < 3 or p in STOP:
        return None
    for raizes, nome, params in DICIONARIO:
        for r in raizes:
            if p == r or (len(r) >= 4 and p.startswith(r)):
                return nome, dict(params)
    return None


def numero_de(palavra):
    p = normal(palavra)
    if p.isdigit():
        return p
    return str(NUMEROS[p]) if p in NUMEROS else None


def _fim_de_frase(p):
    return p["texto"][-1:] in PONTUACAO


def capitulos(P):
    """Comeco de cada capitulo (indice da palavra): corta em fim de frase com pausa, entre 6 e 14 s."""
    inicios, ini = [0], P[0]["inicio"]
    for i in range(len(P) - 1):
        dur = P[i]["fim"] - ini
        pausa = P[i + 1]["inicio"] - P[i]["fim"]
        if _fim_de_frase(P[i]) and ((dur >= CAPITULO_MIN and pausa >= PAUSA_CAPITULO) or dur >= CAPITULO_MAX):
            inicios.append(i + 1)
            ini = P[i + 1]["inicio"]
    return inicios


def cenas(P, inicios_cap):
    """Faixas [a, b] de palavras: 2 a 3,6 s, cortando em pontuacao/pausa, sem atravessar capitulos."""
    fronteiras = set(inicios_cap)
    faixas, a = [], 0
    for i in range(len(P)):
        ultima = i == len(P) - 1
        dur = P[i]["fim"] - P[a]["inicio"]
        pausa = (P[i + 1]["inicio"] - P[i]["fim"]) if not ultima else 9
        quebra_natural = P[i]["texto"][-1:] in PONTUACAO + ",;:" or pausa > PAUSA_CENA
        if ultima or (i + 1) in fronteiras or (dur >= CENA_MIN and quebra_natural) or dur >= CENA_MAX:
            faixas.append([a, i])
            a = i + 1
    juntas = []  # cena curta demais gruda na anterior (se for do mesmo capitulo)
    for f in faixas:
        curta = P[f[1]]["fim"] - P[f[0]]["inicio"] < 1.4
        if juntas and curta and f[0] not in fronteiras:
            juntas[-1][1] = f[1]
        else:
            juntas.append(f)
    return juntas


def _palavra_chave(P, a, b):
    """Prefere palavra com desenho; senao a palavra de conteudo mais longa."""
    candidatas = [i for i in range(a, b + 1) if normal(P[i]["texto"]) not in STOP and len(normal(P[i]["texto"])) >= 3]
    if not candidatas:
        return b
    com_desenho = [i for i in candidatas if desenho_para(P[i]["texto"])]
    if com_desenho:
        return com_desenho[-1]
    return max(candidatas, key=lambda i: (len(normal(P[i]["texto"])), i))


def _modelo_da_cena(P, a, b, zona):
    """Reconhece numero grande, lista e passo a passo dentro da cena."""
    for i in range(a, b + 1):
        n = numero_de(P[i]["texto"])
        if n and normal(P[i]["texto"]) not in ("um", "uma"):
            resto = [P[j]["texto"].strip(".,!?") for j in range(i + 1, min(b + 1, i + 3)) if normal(P[j]["texto"]) not in STOP]
            m = {"tipo": "numero_grande", "em": i, "numero": n, "zona": "topo_direito" if zona != "palco" else "palco"}
            if resto:
                m["rotulo"] = resto[0]
            return m, i
    ordinais = [i for i in range(a, b + 1) if normal(P[i]["texto"]) in ORDINAIS]
    if len(ordinais) >= 2:
        passos = []
        for i in ordinais:
            nxt = next((P[j]["texto"].strip(".,!?") for j in range(i + 1, b + 1) if normal(P[j]["texto"]) not in STOP), P[i]["texto"])
            passos.append({"em": i, "texto": nxt})
        return {"tipo": "passo_a_passo", "passos": passos, "zona": zona}, ordinais[-1]
    # lista: 3 ou mais pedacos curtos separados por virgula
    pedacos, ini = [], a
    for i in range(a, b + 1):
        if P[i]["texto"].endswith(",") or i == b:
            pedacos.append((ini, i))
            ini = i + 1
    curtos = [(x, y) for x, y in pedacos if y - x <= 2]
    if len(curtos) >= 3:
        itens = []
        for x, y in curtos:
            conteudo = [P[j]["texto"].strip(".,!?") for j in range(x, y + 1) if normal(P[j]["texto"]) not in STOP]
            itens.append({"em": x, "texto": conteudo[-1] if conteudo else P[y]["texto"].strip(".,!?")})
        return {"tipo": "lista", "itens": itens, "zona": zona}, curtos[-1][0]
    return None, None


def gerar(P, fonte, inicio, fim, com_video=True, contador=None, chamada=None, cobrir_legenda=False):
    caps = capitulos(P)
    faixas = cenas(P, caps)
    lados = ["lado_direito", "lado_esquerdo"] if com_video else ["palco"]
    roteiro = {"trabalho": "", "fonte": fonte, "inicio": round(inicio, 3), "fim": round(fim, 3),
               "opcoes": {"cobrir_legenda_antiga": cobrir_legenda},
               "capitulos": [{"n": k + (1 if contador else 0), "nome": (contador.format(n=k + 1) if contador else f"parte {k + 1}"),
                              "palavra_inicio": i} for k, i in enumerate(caps)],
               "cenas": [], "elementos": []}
    cap_de = lambda i: max(k for k, c in enumerate(caps) if c <= i)
    if contador:
        for k, c in enumerate(caps):
            roteiro["elementos"].append({"id": f"contador{k + 1}", "desenho": "contador", "texto": contador.format(n=k + 1),
                                         "zona": "topo_esquerdo", "entra": {"em": c, "palavra": P[c]["texto"], "anim": "escrever", "atraso": 0.3}})
    vivos = []  # (elemento, indice da cena) para programar a saida
    for k, (a, b) in enumerate(faixas):
        cid = f"C{k + 1:02d}"
        zona = lados[k % len(lados)]
        cena = {"id": cid, "palavras": [a, b], "metafora": ""}

        def tirar_da_zona(em):
            """Quem estava nesta zona sai quando o desenho novo entra (palco nunca fica vazio)."""
            for el_v, kz in list(vivos):
                if el_v["zona"] == zona and cap_de(faixas[kz][0]) == cap_de(a):
                    el_v["sai"] = {"em": em, "palavra": P[em]["texto"], "anim": "borracha"}
                    vivos.remove((el_v, kz))

        modelo, chave = _modelo_da_cena(P, a, b, zona)
        if modelo:
            tirar_da_zona(_primeira_palavra(modelo))
            # o modelo sai quando a cena seguinte termina (ou fica ate a transicao do capitulo)
            if k + 2 < len(faixas) and cap_de(faixas[k + 2][0]) == cap_de(a):
                modelo["sai_em"] = faixas[k + 2][0]
            cena["modelo"], cena["chave"] = modelo, chave
            cena["metafora"] = f"Modelo “{modelo['tipo'].replace('_', ' ')}”."
            roteiro["cenas"].append(cena)
            continue
        chave = _palavra_chave(P, a, b)
        cena["chave"] = chave
        achado = desenho_para(P[chave]["texto"])
        if achado:
            nome, params = achado
            el = {"id": f"{cid}_{nome}", "desenho": nome, **params,
                  "zona": "perto_da_cabeca" if (nome == "gotas_suor" and com_video) else zona}
            acao = ACAO_DE_IMPACTO.get(nome)
            entrada = ANIMACAO_DE_ENTRADA.get(nome, "pop")
            if acao and chave > a:  # entra antes e reage na palavra-chave
                inicio_el = next((i for i in range(a, chave) if normal(P[i]["texto"]) not in STOP), a)
                el["entra"] = {"em": inicio_el, "palavra": P[inicio_el]["texto"], "anim": entrada}
                el["acoes"] = [{"em": chave, "palavra": P[chave]["texto"], "anim": acao, "impacto": True}]
            else:
                el["entra"] = {"em": chave, "palavra": P[chave]["texto"], "anim": entrada, "impacto": True}
                if entrada in ("escrever", "desenhar", "cair", "fincar", "subir"):
                    el.setdefault("acoes", []).append({"em": chave, "palavra": P[chave]["texto"], "anim": "circular", "atraso": 0.45})
            cena["metafora"] = f"{nome.replace('_', ' ')} na palavra “{P[chave]['texto'].strip('.,!?')}”."
        else:
            texto = P[chave]["texto"].strip(".,!?;:")
            el = {"id": f"{cid}_texto", "desenho": "texto_mao", "texto": texto, "zona": "topo_direito" if com_video else "palco",
                  "entra": {"em": chave, "palavra": P[chave]["texto"], "anim": "escrever_e_circular", "impacto": True}}
            cena["metafora"] = f"Palavra-chave escrita à mão e circulada: “{texto}”. (Troque por um desenho, se quiser.)"
        if el["zona"] == zona:
            tirar_da_zona(el["entra"]["em"])
        roteiro["elementos"].append(el)
        vivos.append((el, k))
        # segundo desenho da cena, em outra palavra (sem impacto)
        for i in range(a, b + 1):
            if i == chave:
                continue
            outro = desenho_para(P[i]["texto"])
            if outro and outro[0] != el["desenho"] and com_video:
                nome2, params2 = outro
                zona2 = lados[(k + 1) % len(lados)]
                el2 = {"id": f"{cid}_{nome2}", "desenho": nome2, **params2, "zona": zona2, "slot": [1, 2],
                       "entra": {"em": i, "palavra": P[i]["texto"], "anim": ANIMACAO_DE_ENTRADA.get(nome2, "pop")},
                       "sai": {"em": min(b + 1, len(P) - 1), "palavra": P[min(b + 1, len(P) - 1)]["texto"], "anim": "puf"}}
                if el2["sai"]["em"] > i:
                    roteiro["elementos"].append(el2)
                break
        roteiro["cenas"].append(cena)
    if chamada:
        alvo = fim - 2.6
        i = min(range(len(P)), key=lambda j: abs(P[j]["inicio"] - alvo))
        ultima = next(c for c in reversed(roteiro["cenas"]) if c["palavras"][0] <= i)
        zona_cta = "abaixo_legenda" if com_video else "palco"
        saida = {"em": i, "palavra": P[i]["texto"], "anim": "borracha"}
        for el in roteiro["elementos"]:  # a chamada final fica sozinha na area dela
            if el["zona"] == zona_cta and ("sai" not in el or el["sai"]["em"] > i) and el["entra"]["em"] < i:
                el["sai"] = dict(saida)
        for c in roteiro["cenas"]:
            m = c.get("modelo")
            if m and m.get("zona") == zona_cta and _primeira_palavra(m) < i and (m.get("sai_em") is None or m["sai_em"] > i):
                m["sai_em"] = i
        roteiro["elementos"] += _chamada(ultima["id"], i, P, chamada, com_video)
    preencher_paradas(roteiro, P)
    return roteiro


def preencher_paradas(roteiro, P, limite=1.5):
    """Onde a tela ficaria sem novidade, um desenho que esta na tela da uma tremidinha."""
    from motor.estilo import ESTILO
    from motor.modelos import expandir
    from motor.roteiro import PARADO_MAX, gatilhos, tempo_gatilho, transicoes

    for _ in range(40):
        exp = expandir(roteiro, P)
        trans = transicoes(exp, P, ESTILO["transicao"]["duracao"])
        desenhos = {tempo_gatilho(P, g) for g in gatilhos(exp)} | {t[k] for t in trans for k in ("inicio", "fim")}
        todos = sorted(desenhos | {p["inicio"] for p in P} | {exp["inicio"], exp["fim"]})
        so_desenhos = sorted(desenhos | {exp["inicio"], exp["fim"]})
        buracos = [(y - x, x, y) for x, y in zip(todos, todos[1:]) if y - x > PARADO_MAX - 0.05]
        buracos += [(y - x, x, y) for x, y in zip(so_desenhos, so_desenhos[1:]) if y - x > limite]
        if not buracos:
            return
        mudou = False
        for _, x, y in sorted(buracos, reverse=True):
            meio = (x + y) / 2
            # se ninguem esta na tela, o ultimo desenho que saiu antes do buraco fica mais um pouco
            vivos_no_meio = [el for el in roteiro["elementos"] if tempo_gatilho(P, el["entra"]) < meio
                             and ("sai" not in el or tempo_gatilho(P, el["sai"]) > meio)]
            if not vivos_no_meio:
                saidos = [el for el in roteiro["elementos"] if "sai" in el and tempo_gatilho(P, el["sai"]) <= meio]
                if saidos:
                    ultimo = max(saidos, key=lambda el: tempo_gatilho(P, el["sai"]))
                    w = min((i for i, p in enumerate(P) if p["inicio"] >= y), default=len(P) - 1)
                    ultimo["sai"] = {**ultimo["sai"], "em": w, "palavra": P[w]["texto"]}
                    mudou = True
                    break
            for el in roteiro["elementos"]:
                t_ent = tempo_gatilho(P, el["entra"])
                t_sai = tempo_gatilho(P, el["sai"]) if "sai" in el else None
                prox = [t["inicio"] for t in trans if t["inicio"] > t_ent]
                some = t_sai if t_sai is not None else (prox[0] if prox else exp["fim"])
                if t_ent + 0.4 < meio < some - 0.3 and not el["zona"].startswith("de:"):
                    w = max(i for i, p in enumerate(P) if p["inicio"] <= meio)
                    acao = {"em": w, "palavra": P[w]["texto"], "anim": "tremer", "atraso": round(meio - P[w]["inicio"], 2)}
                    el.setdefault("acoes", []).append(acao)
                    el["acoes"].sort(key=lambda g: tempo_gatilho(P, g))
                    mudou = True
                    break
            if mudou:
                break
        if not mudou:
            return


def _primeira_palavra(m):
    """Palavra em que o primeiro desenho de um modelo entra."""
    if "em" in m:
        return m["em"]
    for chave in ("itens", "passos"):
        if m.get(chave):
            return min(x["em"] for x in m[chave])
    for chave in ("esquerda", "antes"):
        if chave in m:
            return m[chave]["em"]
    return 0


def _chamada(cid, i, P, texto, com_video):
    from motor.modelos import chamada_para_seguir
    return chamada_para_seguir(f"{cid}_fim", {"em": i, "texto": texto, "zona": "abaixo_legenda" if com_video else "palco"}, P)
