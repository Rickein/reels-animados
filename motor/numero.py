"""Numero grande de cada take, que sobe por tras da cabeca (a pessoa e recolocada por cima com o recorte)."""
from motor import tempo as T
from motor.biblioteca import obter
from motor.desenho import compor
from motor.estilo import ESTILO

NUM = ESTILO["numero_atras"]


class NumerosAtras:
    def __init__(self, lista, trilha_rosto, recorte, fim, transicoes=()):
        self.takes = []
        for k, item in enumerate(sorted(lista, key=lambda x: x["t"])):
            t1 = lista[k + 1]["t"] if k + 1 < len(lista) else fim
            # a subida comeca so quando o rabisco da transicao ja saiu da frente
            subida = max([item["t"]] + [tr["fim"] for tr in transicoes if abs(tr["fim"] - item["t"]) < 0.8])
            self.takes.append((item["t"], t1, str(item["n"]), subida))
        self.rosto, self.recorte = trilha_rosto, recorte
        self._pos = {}

    def take_em(self, t):
        for take in self.takes:
            if take[0] <= t < take[1]:
                return take
        return None

    def _posicao(self, t0, t1):
        """Centro x e topo da cabeca no take inteiro (o ponto mais alto que ela chega), medidos uma vez por take."""
        if t0 not in self._pos:
            cxs, topos = [], []
            t = t0 + 0.3
            while t < t1 - 0.1:
                cab = self.rosto.cabeca_em(t) if self.rosto else None
                if cab:
                    cx = (cab[0] + cab[2]) / 2
                    cxs.append(cx)
                    topos.append(min(cab[1], self.recorte.topo_em(t, cx, (cab[2] - cab[0]) * 0.6) or cab[1]))
                t += 0.4
            cx = sum(cxs) / len(cxs) if cxs else 540
            topo = min(topos) if topos else 600
            # o numero encolhe se nao couber entre o topo da tela e o cabelo
            cabe = (topo - NUM["topo_min"]) / (1 - NUM["sobra_atras_da_cabeca"])
            tamanho = round(min(NUM["tamanho"], NUM["tamanho"] * cabe / (NUM["tamanho"] * 0.95)))
            self._pos[t0] = (cx, topo, max(tamanho, NUM["tamanho_min"]))
        return self._pos[t0]

    def desenhar(self, q, fundo, t):
        """Desenha o numero em q e recoloca a pessoa (do quadro original 'fundo') por cima."""
        take = self.take_em(t)
        if not take:
            return
        t0, t1, n, subida = take
        cx, topo, tamanho = self._posicao(t0, t1)
        img, _ = obter("texto_mao", semente=T.fervura(t, 3), texto=n, tamanho=tamanho, papel=NUM["fonte"], cor=NUM["cor"])
        x = cx - img.width / 2
        y_final = max(NUM["topo_min"], topo - img.height * (1 - NUM["sobra_atras_da_cabeca"]))
        u = T.progresso(t - subida, NUM["atraso"], NUM["subida"])
        if u <= 0:
            return
        y_ini = topo + img.height * 0.4  # escondido atras da cabeca
        y = y_ini + (y_final - y_ini) * T.back_out(u, NUM["passada"])
        es = NUM["esmaecer"]  # depois de subir, vai sumindo atras da pessoa
        k = T.in_out(T.progresso(t - subida, NUM["atraso"] + NUM["subida"] + es["espera"], es["duracao"]))
        opac = 1 - (1 - es["opacidade_final"]) * k
        if opac <= 0.01:
            return
        if opac < 1:
            img = img.copy()
            img.putalpha(img.getchannel("A").point(lambda v: round(v * opac)))
        compor(q, img, round(x), round(y))
        pessoa = fundo.convert("RGBA")
        pessoa.putalpha(self.recorte.mascara_em(t, q.size))
        q.alpha_composite(pessoa)

    def caixas(self):
        """(inicio, fim, caixa) de cada numero enquanto aparece: os desenhos desviam dele."""
        es = NUM["esmaecer"]
        out = []
        for t0, t1, n, subida in self.takes:
            cx, topo, tamanho = self._posicao(t0, t1)
            img, _ = obter("texto_mao", semente=0, texto=n, tamanho=tamanho, papel=NUM["fonte"], cor=NUM["cor"])
            y = max(NUM["topo_min"], topo - img.height * (1 - NUM["sobra_atras_da_cabeca"]))
            fim = subida + NUM["atraso"] + NUM["subida"] + es["espera"] + es["duracao"] * 0.7
            out.append((subida, fim, (cx - img.width / 2, y, cx + img.width / 2, y + img.height)))
        return out

    def gatilhos(self):
        return [(subida + NUM["atraso"], "numero") for _, _, _, subida in self.takes]
