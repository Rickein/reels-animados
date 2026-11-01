"""Audio: extrai/converte com ffmpeg e le WAV em numpy (sem depender do PyAV)."""
import subprocess
import wave
from pathlib import Path

import numpy as np

from motor.ambiente import achar_ffmpeg

TAXA_WHISPER = 16000


def extrair_wav(entrada, saida, taxa=TAXA_WHISPER, inicio=None, duracao=None) -> Path:
    """Converte qualquer audio/video (m4a, mp3, wav, mp4...) em WAV mono 16 bits."""
    cmd = [achar_ffmpeg(), "-y", "-hide_banner", "-loglevel", "error"]
    if inicio is not None:
        cmd += ["-ss", str(inicio)]
    if duracao is not None:
        cmd += ["-t", str(duracao)]
    cmd += ["-i", str(entrada), "-vn", "-ac", "1", "-ar", str(taxa), "-c:a", "pcm_s16le", str(saida)]
    subprocess.run(cmd, check=True)
    return Path(saida)


def info_midia(caminho) -> dict:
    """Duracao e se tem imagem (video) ou so som (m4a, mp3, wav...)."""
    import json
    saida = subprocess.run([achar_ffmpeg("ffprobe"), "-v", "error",
                            "-show_entries", "stream=codec_type,width,height:stream_disposition=attached_pic:format=duration",
                            "-of", "json", str(caminho)], capture_output=True, text=True, check=True).stdout
    dados = json.loads(saida)
    videos = [s for s in dados.get("streams", []) if s.get("codec_type") == "video"
              and not s.get("disposition", {}).get("attached_pic")]  # capa de mp3 nao conta como video
    return {"duracao": float(dados["format"]["duration"]), "tem_video": bool(videos),
            "largura": videos[0]["width"] if videos else None, "altura": videos[0]["height"] if videos else None}


def ler_wav(caminho) -> np.ndarray:
    """Le um WAV PCM 16 bits mono como float32 entre -1 e 1 (formato que o faster-whisper aceita)."""
    with wave.open(str(caminho), "rb") as w:
        if w.getsampwidth() != 2 or w.getnchannels() != 1:
            raise ValueError("esperado WAV mono 16 bits (use extrair_wav)")
        dados = w.readframes(w.getnframes())
    return np.frombuffer(dados, dtype=np.int16).astype(np.float32) / 32768.0
