"""Som: efeitos sintetizados no proprio codigo (caneta, rangido, pop, boing, pagina) e mixagem com a voz.

Cada efeito e ajustado para ficar ~17 dB abaixo da voz (estilo.json) e o resultado final e
normalizado em -14 LUFS pelo ffmpeg (duas passadas, para acertar o volume de verdade).
"""
import json
import random
import subprocess
import wave

import numpy as np

from motor.ambiente import achar_ffmpeg
from motor.estilo import ESTILO

TAXA = 48000
SONS = ESTILO["sons"]
EF = SONS["efeitos"]

# qual som cada animacao faz
SOM_DA_ANIMACAO = {
    "escrever": "escrever", "escrever_e_circular": "escrever", "desenhar": "escrever", "riscar": "riscar",
    "circular": "riscar", "borracha": "riscar",
    "pop": "objeto_entra", "colar": "objeto_entra", "cair": "objeto_entra", "fincar": "objeto_entra",
    "subir": "objeto_entra", "acender": "objeto_entra", "borrifar": "objeto_entra", "procurar": "objeto_entra",
    "balancar": "objeto_entra", "balancar_e_circular": "objeto_entra", "boina": "objeto_entra",
    "virar_pao_frances": "objeto_entra", "multiplicar": "objeto_entra", "puf": "objeto_entra",
    "desenrolar": "seta", "desenrolar_longo": "seta", "malabarismo": "seta", "despencar": "seta",
    "medir_angulo": "seta", "voar_longe": "seta",
    "abandonar": "objeto_entra", "marcar_dias": "escrever", "contar_riscos": "riscar", "esvaziar": "seta",
    "pintar_fds": "objeto_entra", "transbordar": "objeto_entra",
    "contar_numero": "objeto_entra", "marcar": "riscar",
}
PRIORIDADE = {"impacto": 3, "transicao": 2}


def _ruido_filtrado(n, f_baixa, f_alta, semente):
    """Ruido branco filtrado numa faixa de frequencia (pela FFT)."""
    r = np.random.default_rng(semente)
    x = r.standard_normal(n)
    espectro = np.fft.rfft(x)
    freqs = np.fft.rfftfreq(n, 1 / TAXA)
    espectro[(freqs < f_baixa) | (freqs > f_alta)] = 0
    y = np.fft.irfft(espectro, n)
    return y / (np.max(np.abs(y)) + 1e-9)


def _envelope(n, ataque=0.004, decaimento=None):
    t = np.arange(n) / TAXA
    env = np.minimum(1.0, t / ataque)
    if decaimento:
        env *= np.exp(-t / decaimento)
    else:
        env *= np.clip(1 - t / (n / TAXA), 0, 1) ** 2
    return env


def _varredura(f0, f1, dur, forma="seno"):
    n = int(dur * TAXA)
    t = np.arange(n) / TAXA
    f = f0 * (f1 / f0) ** (t / dur)
    fase = 2 * np.pi * np.cumsum(f) / TAXA
    return np.sin(fase), n


def caneta(duracao=None, semente=0):
    c = EF["caneta"]
    rajadas = c["rajadas"] if duracao is None else max(4, int(duracao / c["intervalo"]))
    n = int((rajadas * c["intervalo"] + c["duracao_rajada"]) * TAXA)
    sinal = np.zeros(n)
    r = random.Random(semente)
    for i in range(rajadas):
        m = int(c["duracao_rajada"] * TAXA)
        centro = r.uniform(*c["freq_hz"])
        rajada = _ruido_filtrado(m, centro / (1 + 1 / c["q"]), centro * (1 + 1 / c["q"]), semente * 100 + i)
        ini = int(i * c["intervalo"] * TAXA)
        sinal[ini:ini + m] += rajada * _envelope(m, 0.002) * r.uniform(0.6, 1.0)
    return sinal


def rangido(semente=0):
    c = EF["rangido"]
    a, n = _varredura(c["f0"], c["f1"], c["duracao"])
    b, _ = _varredura(c["f0"] * 1.03, c["f1"] * 0.97, c["duracao"])
    return (a + 0.5 * b) * _envelope(n, 0.01)


def pop(semente=0):
    c = EF["pop"]
    s, n = _varredura(c["f0"], c["f1"], c["duracao"])
    return s * _envelope(n, 0.002, c["duracao"] / 3)


def boing(semente=0):
    c = EF["boing"]
    n = int(c["duracao"] * TAXA)
    t = np.arange(n) / TAXA
    subida = 0.09
    f = np.where(t < subida, c["f0"] * (c["pico"] / c["f0"]) ** (t / subida),
                 c["pico"] * (c["f1"] / c["pico"]) ** ((t - subida) / (c["duracao"] - subida)))
    f = f + c["vibrato_prof_hz"] * np.sin(2 * np.pi * c["vibrato_hz"] * t)
    return np.sin(2 * np.pi * np.cumsum(f) / TAXA) * _envelope(n, 0.008, c["duracao"] / 3)


def pagina(semente=0, nome="pagina"):
    c = EF[nome]
    n = int(c["duracao"] * TAXA)
    partes = 8
    sinal = np.zeros(n)
    for k in range(partes):  # varredura: faixas cada vez mais agudas, que se sobrepoem
        ini, fim = int(n * k / partes), int(n * (k + 2) / partes)
        fim = min(n, fim)
        fc = c["f0"] * (c["f1"] / c["f0"]) ** (k / (partes - 1))
        trecho = _ruido_filtrado(fim - ini, fc * 0.6, fc * 1.6, semente * 10 + k)
        sinal[ini:fim] += trecho * np.hanning(fim - ini)
    t = np.arange(n) / n
    return sinal * np.sin(np.pi * t) ** 0.7


GERADORES = {"caneta": caneta, "rangido": rangido, "pop": pop, "boing": boing, "pagina": pagina,
             "pagina_suave": lambda semente=0: pagina(semente, "pagina_suave")}


def ler_audio(caminho_video, taxa=TAXA):
    """Audio do video em float32 mono."""
    proc = subprocess.run([achar_ffmpeg(), "-v", "error", "-i", str(caminho_video), "-vn", "-ac", "1", "-ar", str(taxa),
                           "-f", "f32le", "-"], capture_output=True, check=True)
    return np.frombuffer(proc.stdout, np.float32)


def eventos_do_filme(filme):
    """(instante, categoria) de cada som: animacoes, impactos e transicoes. Evita amontoar sons."""
    brutos = []
    for a in filme.atores:
        for t, anim, impacto in a.gatilhos():
            cat = SOM_DA_ANIMACAO.get(anim)
            if a.nome.startswith("seta") and anim == "desenhar":
                cat = "seta"
            if cat:
                brutos.append((t, cat))
            if impacto:
                brutos.append((t, "impacto"))
    for tr in filme.transicoes:
        if not tr.get("corte"):
            brutos.append((tr["inicio"], "transicao"))
    brutos.sort()
    eventos = []
    for t, cat in brutos:  # dois sons comuns a menos de 90 ms: fica so o mais importante
        if eventos and t - eventos[-1][0] < 0.09 and cat != "impacto" and eventos[-1][1] != "impacto":
            if PRIORIDADE.get(cat, 0) > PRIORIDADE.get(eventos[-1][1], 0):
                eventos[-1] = (t, cat)
            continue
        if eventos and cat == eventos[-1][1] and t - eventos[-1][0] < 0.09:
            continue
        eventos.append((t, cat))
    return eventos


def filtrar(eventos, opcoes):
    """Com "opcoes": {"sons": {"categorias": [...], "troca": {"transicao": "pagina_suave"}}} so tocam essas categorias,
    e cada uma pode usar outro efeito. A troca vira a categoria "efeito:nome"."""
    cfg = opcoes.get("sons")
    if not cfg:
        return eventos
    troca = cfg.get("troca", {})
    return [(t, f"efeito:{troca[c]}" if c in troca else c) for t, c in eventos if c in cfg["categorias"]]


def faixa_de_efeitos(eventos, duracao, voz):
    """Monta a faixa de efeitos: cada som com volume ~17 dB abaixo da voz falada."""
    ativa = voz[np.abs(voz) > 0.02]
    rms_voz = float(np.sqrt(np.mean(ativa ** 2))) if ativa.size else 0.1
    alvo = rms_voz * 10 ** (SONS["volume_relativo_db"] / 20)
    faixa = np.zeros(int(duracao * TAXA) + TAXA)
    gatilhos = SONS["gatilhos"]
    for i, (t, cat) in enumerate(eventos):
        nome = cat.split(":", 1)[1] if cat.startswith("efeito:") else gatilhos.get(cat)
        if not nome:
            continue
        s = GERADORES[nome](semente=i)
        ativo = s[np.abs(s) > 0.05 * np.max(np.abs(s))]
        rms = float(np.sqrt(np.mean(ativo ** 2))) if ativo.size else 1.0
        s = s * (alvo / rms)
        if cat == "riscar":
            s *= 0.7
        s *= 10 ** (EF[nome].get("ganho_db", 0) / 20)
        ini = int(t * TAXA)
        fim = min(len(faixa), ini + len(s))
        faixa[ini:fim] += s[:fim - ini]
    return faixa[:int(duracao * TAXA)]


def salvar_wav(caminho, sinal, taxa=TAXA):
    pico = np.max(np.abs(sinal)) if sinal.size else 0
    if pico > 0.99:
        sinal = sinal * (0.99 / pico)
    dados = (sinal * 32767).astype(np.int16)
    with wave.open(str(caminho), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(taxa)
        w.writeframes(dados.tobytes())


def mixar(video, efeitos_wav, saida_wav, inicio=0.0, duracao=None):
    """Voz original + efeitos, normalizado em -14 LUFS (loudnorm em duas passadas)."""
    aud = ESTILO["saida"]["audio"]
    corte = ["-ss", str(inicio)] + (["-t", str(duracao)] if duracao else [])
    entradas = [*corte, "-i", str(video), *corte, "-i", str(efeitos_wav)]
    filtro = "[0:a]aresample=48000,pan=mono|c0=c0[v];[v][1:a]amix=inputs=2:normalize=0:duration=first[m]"
    ln = f"loudnorm=I={aud['lufs']}:TP={aud['pico_real_db']}:LRA=11"
    ff = achar_ffmpeg()
    medir = subprocess.run([ff, "-hide_banner", "-nostats", *entradas,
                            "-filter_complex", f"{filtro};[m]{ln}:print_format=json", "-f", "null", "-"],
                           capture_output=True, text=True, check=True)
    txt = medir.stderr
    m = json.loads(txt[txt.rfind("{"):txt.rfind("}") + 1])
    ln2 = (f"{ln}:measured_I={m['input_i']}:measured_TP={m['input_tp']}:measured_LRA={m['input_lra']}"
           f":measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true")
    subprocess.run([ff, "-y", "-hide_banner", "-loglevel", "error", *entradas,
                    "-filter_complex", f"{filtro};[m]{ln2},aresample=48000", "-ac", "2", str(saida_wav)], check=True)
    return float(m["input_i"])
