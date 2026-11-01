"""Mostra as 6 cenas modelo funcionando (e serve de exemplo de roteiro com modelos).

Cria o trabalho 'modelos-demo' com uma fala de mentira (tempos sinteticos), monta um roteiro que usa
lista, comparacao, numero grande, antes e depois, passo a passo e chamada para seguir, valida e gera
biblioteca/modelos_demo.png com um quadro de cada.

Uso:  .venv\\Scripts\\python ferramentas\\demo_modelos.py
"""
import json
import sys
import wave
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from motor.ambiente import RAIZ  # noqa: E402

FALAS = [
    "Três coisas que você precisa: água, sono, proteína.",
    "Dieta da moda ou comida de verdade? Comida de verdade.",
    "Oitenta por cento é hábito, não força de vontade.",
    "Antes era culpa. Depois virou equilíbrio.",
    "Primeiro planeje, segundo coma, terceiro descanse.",
    "Me segue pra mais verdades.",
]


def palavras_sinteticas():
    P, t, inicios = [], 0.3, []
    for frase in FALAS:
        inicios.append(len(P))
        for w in frase.split():
            P.append({"i": len(P), "texto": w, "inicio": round(t, 3), "fim": round(t + 0.3, 3), "confianca": 1.0})
            t += 0.34 + (0.22 if w[-1] in ".?" else 0)
        t += 1.2  # pausa entre capitulos: cabe a transicao e da tempo de ver o modelo inteiro
    return P, inicios, P[-1]["fim"] + 0.45


def achar(P, ini, texto):
    """Indice da primeira palavra (a partir de ini) que comeca com texto."""
    return next(i for i in range(ini, len(P)) if P[i]["texto"].lower().strip(".,:?").startswith(texto.lower()))


def main():
    P, ini, dur = palavras_sinteticas()
    pasta = RAIZ / "trabalhos" / "modelos-demo"
    pasta.mkdir(parents=True, exist_ok=True)
    with wave.open(str(pasta / "silencio.wav"), "wb") as w:  # a demo nao tem voz
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(48000)
        w.writeframes(b"\x00\x00" * int(48000 * dur))
    (pasta / "palavras.json").write_text(json.dumps({"palavras": P}, ensure_ascii=False), encoding="utf-8")
    fim_cap = lambda k: (ini[k + 1] - 1) if k + 1 < len(ini) else len(P) - 1
    cena = lambda k, metafora, modelo: {"id": f"M{k + 1}", "palavras": [ini[k], fim_cap(k)], "metafora": metafora, "modelo": modelo}
    roteiro = {
        "trabalho": "modelos-demo", "fonte": "trabalhos/modelos-demo/silencio.wav", "inicio": 0.0, "fim": round(dur, 3),
        "opcoes": {"cobrir_legenda_antiga": False},
        "capitulos": [{"n": k, "nome": f"modelo {k + 1}", "palavra_inicio": i} for k, i in enumerate(ini)],
        "cenas": [
            cena(0, "Lista: cada item entra quando é falado.", {"tipo": "lista", "zona": "palco", "itens": [
                {"em": achar(P, ini[0], "água"), "texto": "água", "marcar_em": achar(P, ini[0], "proteína")},
                {"em": achar(P, ini[0], "sono"), "texto": "sono"},
                {"em": achar(P, ini[0], "proteína"), "texto": "proteína"}]}),
            cena(1, "Comparação com veredito.", {"tipo": "comparacao", "zona": "palco",
                 "esquerda": {"em": achar(P, ini[1], "dieta"), "texto": "dieta da moda"},
                 "direita": {"em": achar(P, ini[1], "comida"), "desenho": "prato_salada"},
                 "veredito": {"em": achar(P, achar(P, ini[1], "verdade") + 1, "comida"), "vencedor": "direita"}}),
            cena(2, "Número grande que conta até o valor.", {"tipo": "numero_grande", "zona": "palco",
                 "em": achar(P, ini[2], "oitenta"), "numero": "80", "rotulo": "% é hábito"}),
            cena(3, "Antes e depois.", {"tipo": "antes_depois", "zona": "palco",
                 "antes": {"em": achar(P, ini[3], "culpa"), "desenho": "gotas_suor"},
                 "depois": {"em": achar(P, ini[3], "equilíbrio"), "desenho": "balanca", "texto": ""}}),
            cena(4, "Passo a passo numerado.", {"tipo": "passo_a_passo", "zona": "palco", "passos": [
                {"em": achar(P, ini[4], "primeiro"), "texto": "planeje"},
                {"em": achar(P, ini[4], "segundo"), "texto": "coma"},
                {"em": achar(P, ini[4], "terceiro"), "texto": "descanse"}]}),
            cena(5, "Chamada para seguir.", {"tipo": "chamada_para_seguir", "zona": "palco", "impacto": True,
                 "em": achar(P, ini[5], "segue"), "texto": "me segue pra mais verdades!"}),
        ],
        "elementos": [],
    }
    from motor.rascunho import preencher_paradas
    preencher_paradas(roteiro, P)
    (pasta / "roteiro.json").write_text(json.dumps(roteiro, ensure_ascii=False, indent=1), encoding="utf-8")

    from motor.render import Motor
    from motor.roteiro import carregar, validar
    _, rot, palavras, estilo = carregar("modelos-demo")
    erros, avisos, _ = validar(rot, palavras, estilo)
    for e in erros:
        print("ERRO:", e)
    motor = Motor("modelos-demo")
    # logo antes da transicao: todos os desenhos do modelo ja entraram e terminaram de animar
    inicio_trans = {tr["capitulo"]: tr["inicio"] for tr in motor.filme.transicoes}
    instantes = [(inicio_trans.get(k + 1, dur) - 0.05, f"modelo {k + 1}") for k in range(len(FALAS))]
    nomes = ["lista", "comparação", "número grande", "antes e depois", "passo a passo", "chamada p/ seguir"]
    folha, _ = motor.previa([(round(t, 2), n) for (t, _), n in zip(instantes, nomes)], colunas=6)
    destino = RAIZ / "biblioteca" / "modelos_demo.png"
    folha.save(destino)
    print(f"{len(rot['elementos'])} desenhos gerados pelos modelos · {len(erros)} erro(s) · {destino}")


if __name__ == "__main__":
    main()
