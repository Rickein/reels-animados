"""Transcricao com o tempo de cada palavra (faster-whisper) e revisao humana do texto."""
import difflib
import json
import re
import time
from datetime import datetime
from pathlib import Path

from motor.ambiente import PASTA_MODELOS, gpu_disponivel
from motor.audio import TAXA_WHISPER, extrair_wav, ler_wav

MODELO_PADRAO = "large-v3-turbo"
MODELO_CPU = "small"
CONFIANCA_BAIXA = 0.5
_LINHA_REVISAO = re.compile(r"^\[(\d+):(\d+(?:\.\d+)?)\]\s*(.*)$")


def transcrever(entrada, pasta, modelo=MODELO_PADRAO, idioma="pt", dica=None) -> dict:
    """Converte a entrada em WAV 16 kHz, transcreve e devolve frases + palavras com inicio/fim em segundos."""
    pasta = Path(pasta)
    pasta.mkdir(parents=True, exist_ok=True)
    audio = ler_wav(extrair_wav(entrada, pasta / "audio_16k.wav"))

    from faster_whisper import WhisperModel
    dispositivo, tipo = ("cuda", "float16") if gpu_disponivel() else ("cpu", "int8")
    if dispositivo == "cpu" and modelo == MODELO_PADRAO:
        modelo = MODELO_CPU
    t0 = time.time()
    m = WhisperModel(modelo, device=dispositivo, compute_type=tipo, download_root=str(PASTA_MODELOS))
    segmentos, _ = m.transcribe(audio, language=idioma, word_timestamps=True, vad_filter=True,
                                beam_size=5, initial_prompt=dica)

    palavras, frases = [], []
    for s in segmentos:
        ini = len(palavras)
        for w in s.words:
            txt = w.word.strip()
            if txt:
                palavras.append({"i": len(palavras), "texto": txt, "inicio": round(w.start, 3),
                                 "fim": round(w.end, 3), "confianca": round(w.probability, 3)})
        if len(palavras) > ini:
            frases.append({"inicio": palavras[ini]["inicio"], "fim": palavras[-1]["fim"], "palavras": [ini, len(palavras)]})

    return {
        "fonte": str(Path(entrada).resolve()),
        "modelo": modelo, "dispositivo": dispositivo, "idioma": idioma,
        "duracao_audio": round(len(audio) / TAXA_WHISPER, 3),
        "tempo_processamento": round(time.time() - t0, 1),
        "criado_em": datetime.now().isoformat(timespec="seconds"),
        "revisado": False,
        "frases": frases,
        "palavras": palavras,
    }


def salvar_json(caminho, dados) -> None:
    Path(caminho).write_text(json.dumps(dados, ensure_ascii=False, indent=1), encoding="utf-8")


def tempo_fmt(s: float) -> str:
    return f"{int(s // 60):02d}:{s % 60:04.1f}"


def texto_da_frase(dados, frase) -> str:
    a, b = frase["palavras"]
    return " ".join(p["texto"] for p in dados["palavras"][a:b])


def gerar_revisao(dados) -> str:
    """Texto para a pessoa corrigir: uma frase por linha, com o tempo em que ela comeca."""
    duvidas = [p for p in dados["palavras"] if p["confianca"] < CONFIANCA_BAIXA]
    linhas = [
        "# REVISAO DO TEXTO",
        "# Corrija as palavras erradas direto nas linhas abaixo (pode trocar, juntar ou separar palavras).",
        "# Mantenha o [tempo] no inicio de cada linha. Linhas que comecam com # sao ignoradas.",
        "# Depois rode:  .venv\\Scripts\\python transcrever.py <arquivo> --aplicar",
    ]
    if duvidas:
        linhas.append("# Palavras com baixa confianca (confira estas primeiro): "
                      + ", ".join(f"\"{p['texto']}\" ({tempo_fmt(p['inicio'])})" for p in duvidas))
    linhas.append("")
    linhas += [f"[{tempo_fmt(f['inicio'])}] {texto_da_frase(dados, f)}" for f in dados["frases"]]
    return "\n".join(linhas) + "\n"


def _norm(s: str) -> str:
    return re.sub(r"[^\w]", "", s.lower())


def _retemporizar(orig, novos):
    """Alinha as palavras corrigidas com as originais e reaproveita os tempos.
    Trocas 1 por 1 mantem o tempo; quando muda a quantidade, o trecho e dividido pelo tamanho das palavras."""
    orig = [dict(p) for p in orig]
    sm = difflib.SequenceMatcher(a=[_norm(p["texto"]) for p in orig], b=[_norm(t) for t in novos], autojunk=False)
    saida = []
    herdado = None  # tempo de palavras apagadas: passa para a proxima palavra (ou para a anterior, no fim da frase)

    def adicionar(p):
        nonlocal herdado
        if herdado is not None:
            p["inicio"] = min(p["inicio"], herdado[0])
            herdado = None
        saida.append(p)

    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op == "delete":
            herdado = (herdado[0] if herdado else orig[i1]["inicio"], orig[i2 - 1]["fim"])
            continue
        if op == "equal" or (op == "replace" and i2 - i1 == j2 - j1):
            for k in range(i2 - i1):
                p = {**orig[i1 + k], "texto": novos[j1 + k]}
                if novos[j1 + k] != orig[i1 + k]["texto"]:
                    p.update(confianca=1.0, editada=True)
                adicionar(p)
            continue
        if i2 > i1:
            ini, fim = orig[i1]["inicio"], orig[i2 - 1]["fim"]
        elif herdado:  # palavra nova logo depois de uma apagada: usa o tempo dela
            ini, fim, herdado = herdado[0], herdado[1], None
        elif saida:  # palavra nova sem par: divide o tempo da palavra anterior
            ant = saida[-1]
            meio = round((ant["inicio"] + ant["fim"]) / 2, 3)
            ini, fim, ant["fim"] = meio, ant["fim"], meio
        else:  # palavra nova no comeco: divide o tempo da proxima
            prox = orig[i1]
            meio = round((prox["inicio"] + prox["fim"]) / 2, 3)
            ini, fim, prox["inicio"] = prox["inicio"], meio, meio
        pesos = [max(1, len(t)) for t in novos[j1:j2]]
        t = ini
        for tok, w in zip(novos[j1:j2], pesos):
            d = (fim - ini) * w / sum(pesos)
            adicionar({"texto": tok, "inicio": round(t, 3), "fim": round(t + d, 3), "confianca": 1.0, "editada": True})
            t += d
    if herdado and saida:
        saida[-1]["fim"] = max(saida[-1]["fim"], herdado[1])
    return saida


def aplicar_revisao(original: dict, texto: str) -> dict:
    """Aplica o revisao.txt editado sobre a transcricao original (pode ser repetido quantas vezes quiser)."""
    linhas = [m.group(3) for m in map(_LINHA_REVISAO.match, texto.splitlines()) if m]
    if len(linhas) != len(original["frases"]):
        raise ValueError(f"o revisao.txt tem {len(linhas)} linhas com [tempo], mas a transcricao tem "
                         f"{len(original['frases'])} frases. Nao apague nem crie linhas, so corrija o texto.")
    palavras, frases = [], []
    for frase, linha in zip(original["frases"], linhas):
        a, b = frase["palavras"]
        novas = _retemporizar(original["palavras"][a:b], linha.split())
        if not novas:
            continue
        ini = len(palavras)
        for p in novas:
            p["i"] = len(palavras)
            palavras.append(p)
        frases.append({"inicio": palavras[ini]["inicio"], "fim": palavras[-1]["fim"], "palavras": [ini, len(palavras)]})
    return {**original, "revisado": True, "revisado_em": datetime.now().isoformat(timespec="seconds"),
            "frases": frases, "palavras": palavras}
