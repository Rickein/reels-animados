"""Recorte da pessoa (MODNet) para desenhar coisas ATRAS dela, como o numero que sobe por tras da cabeca.

A mascara de cada quadro e calculada uma vez em baixa resolucao e guardada em cache no trabalho (recorte.npz).
"""
import subprocess

import numpy as np
from PIL import Image

from motor.ambiente import PASTA_MODELOS, achar_ffmpeg

MODELO = PASTA_MODELOS / "modnet" / "modnet.onnx"
LARG, ALT = 288, 512  # 9:16, multiplos de 32 (o MODNet pede)


def _quadros(video, fps):
    filtro = f"scale={LARG}:{ALT}:force_original_aspect_ratio=increase,crop={LARG}:{ALT},fps={fps}"
    cmd = [achar_ffmpeg(), "-v", "error", "-i", str(video), "-vf", filtro, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, bufsize=10 ** 7)
    tam = LARG * ALT * 3
    try:
        while True:
            buf = proc.stdout.read(tam)
            if len(buf) < tam:
                break
            yield np.frombuffer(buf, np.uint8).reshape(ALT, LARG, 3)
    finally:
        proc.stdout.close()
        proc.wait()


class TrilhaRecorte:
    def __init__(self, video, cache, fps=30):
        self.fps = fps
        if cache.exists():
            self.mascaras = np.load(cache)["m"]
        else:
            import onnxruntime as ort
            sess = ort.InferenceSession(str(MODELO), providers=["CPUExecutionProvider"])
            nome = sess.get_inputs()[0].name
            saida = []
            for i, q in enumerate(_quadros(video, fps)):
                x = (q.astype(np.float32) / 127.5 - 1.0).transpose(2, 0, 1)[None]
                a = sess.run(None, {nome: x})[0][0, 0]
                saida.append(np.clip(a * 255, 0, 255).astype(np.uint8))
                if i % 150 == 0:
                    print(f"  recorte: {i / fps:.0f}s", flush=True)
            self.mascaras = np.stack(saida)
            np.savez_compressed(cache, m=self.mascaras)

    def mascara_em(self, t, tamanho):
        """Mascara (L) da pessoa no instante t, ja no tamanho do quadro."""
        i = min(max(0, round(t * self.fps)), len(self.mascaras) - 1)
        return Image.fromarray(self.mascaras[i]).resize(tamanho, Image.BILINEAR)

    def topo_em(self, t, cx, largura, quadro=(1080, 1920)):
        """y (no quadro) do ponto mais alto da pessoa numa faixa de 'largura' px centrada em cx, ou None."""
        m = np.asarray(self.mascara_em(t, (LARG, ALT)))
        k = LARG / quadro[0]
        faixa = m[:, max(0, round((cx - largura / 2) * k)):round((cx + largura / 2) * k)] > 128
        linhas = np.flatnonzero(faixa.any(axis=1))
        return linhas[0] / k if len(linhas) else None
