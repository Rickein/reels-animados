"""Confere se tudo que o projeto precisa esta instalado e funcionando.

Uso:  .venv\\Scripts\\python testar_ambiente.py
"""
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from motor.ambiente import PASTA_MODELOS, RAIZ, achar_ffmpeg, gpu_disponivel
from motor.audio import extrair_wav, ler_wav

PESOS = {100: "Thin", 200: "ExtraLight", 300: "Light", 400: "Regular", 500: "Medium",
         600: "SemiBold", 700: "Bold", 800: "ExtraBold", 900: "Black"}
TEMP = Path(tempfile.gettempdir())
resultados = []


def item(nome, func):
    try:
        info = func()
        resultados.append(True)
        print(f"[ OK ]   {nome}: {info}")
    except Exception as e:  # o objetivo aqui e listar tudo que falhou, sem parar no primeiro erro
        resultados.append(False)
        print(f"[FALHOU] {nome}: {e}")


def t_python():
    return sys.version.split()[0]


def t_bibliotecas():
    import cv2
    import ctranslate2
    import faster_whisper
    import numpy
    import PIL
    return (f"numpy {numpy.__version__} · pillow {PIL.__version__} · opencv {cv2.__version__} · "
            f"faster-whisper {faster_whisper.__version__} · ctranslate2 {ctranslate2.__version__}")


def t_ffmpeg():
    ff = achar_ffmpeg()
    versao = subprocess.run([ff, "-hide_banner", "-version"], capture_output=True, text=True).stdout.split("\n")[0]
    encoders = subprocess.run([ff, "-hide_banner", "-encoders"], capture_output=True, text=True).stdout
    filtros = subprocess.run([ff, "-hide_banner", "-filters"], capture_output=True, text=True).stdout
    faltando = [n for n, txt in (("libx264", encoders), ("aac", encoders), ("loudnorm", filtros)) if n not in txt]
    if faltando:
        raise RuntimeError("recursos faltando: " + ", ".join(faltando))
    return versao + " (H.264, AAC e loudnorm ok)"


def t_fontes():
    from PIL import Image, ImageDraw, ImageFont
    estilo = json.loads((RAIZ / "estilo.json").read_text(encoding="utf-8"))
    img = Image.new("RGB", (1080, 120 * len(estilo["fontes"]) + 40), estilo["cores"]["fundo"]["hex"])
    d = ImageDraw.Draw(img)
    nomes = []
    for i, (papel, f) in enumerate(estilo["fontes"].items()):
        fonte = ImageFont.truetype(str(RAIZ / f["arquivo"]), 72)
        if "variavel" in f:
            fonte.set_variation_by_name(PESOS[f["variavel"]["wght"]])
        d.text((30, 30 + i * 120), "Ação, pão, carboidrato!", font=fonte, fill=estilo["cores"]["principal"]["hex"])
        nomes.append(f"{papel}={f['familia']}")
    amostra = TEMP / "teste_fontes.png"
    img.save(amostra)
    return " · ".join(nomes) + f" (amostra em {amostra})"


def t_modelos():
    faltando = [n for n in ("face_detection_yunet_2023mar.onnx", "modnet/modnet.onnx") if not (PASTA_MODELOS / n).exists()]
    if faltando:
        raise RuntimeError("faltando em modelos/: " + ", ".join(faltando) + " (rode instalar.ps1)")
    return "rosto (YuNet) e recorte (MODNet) ok"


def t_gpu():
    if not gpu_disponivel():
        raise RuntimeError("nenhuma GPU CUDA visivel")
    import ctranslate2
    return f"{ctranslate2.get_cuda_device_count()} GPU · tipos: {', '.join(sorted(ctranslate2.get_supported_compute_types('cuda')))}"


def t_transcricao():
    """Corta 6 s do video bruto e transcreve com o modelo 'tiny' (so para testar a GPU de verdade)."""
    video = next((p for p in sorted((RAIZ / "Bruto").iterdir()) if p.is_file() and not p.name.startswith(".")), None)
    if video is None:
        return "pulado (coloque um video em Bruto/ para testar a transcricao)"
    wav = extrair_wav(video, TEMP / "teste_ambiente.wav", inicio=4.5, duracao=6)
    from faster_whisper import WhisperModel
    dispositivo, tipo = ("cuda", "float16") if gpu_disponivel() else ("cpu", "int8")
    t0 = time.time()
    modelo = WhisperModel("tiny", device=dispositivo, compute_type=tipo, download_root=str(PASTA_MODELOS))
    segmentos, _ = modelo.transcribe(ler_wav(wav), language="pt", word_timestamps=True)
    palavras = [p for s in segmentos for p in s.words]
    texto = " ".join(p.word.strip() for p in palavras)
    return f"{len(palavras)} palavras com tempo em {time.time() - t0:.1f}s ({dispositivo}): \"{texto}\""


if __name__ == "__main__":
    print("Testando o ambiente do projeto...\n")
    item("Python", t_python)
    item("Bibliotecas", t_bibliotecas)
    item("ffmpeg", t_ffmpeg)
    item("Fontes do estilo", t_fontes)
    item("Modelos de rosto e recorte", t_modelos)
    item("Placa de video (CUDA)", t_gpu)
    item("Transcricao de teste", t_transcricao)
    ok = sum(resultados)
    print(f"\n{ok}/{len(resultados)} testes passaram.")
    sys.exit(0 if all(resultados) else 1)
