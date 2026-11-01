"""Acha o rosto no quadro (YuNet, do OpenCV) para os desenhos nunca cobrirem a cara de quem fala."""
import cv2
import numpy as np

from motor.ambiente import PASTA_MODELOS
from motor.estilo import ESTILO

MODELO = PASTA_MODELOS / "face_detection_yunet_2023mar.onnx"


class DetectorRosto:
    def __init__(self, confianca=0.7):
        self._det = None
        self.confianca = confianca

    def achar(self, quadro_bgr: np.ndarray):
        """Caixa (x0, y0, x1, y1) do maior rosto, em pixels do proprio quadro, ou None."""
        h, w = quadro_bgr.shape[:2]
        if self._det is None:
            # o OpenCV nao abre caminhos com acento (ex.: "Gonçalves"); por isso o modelo vai pela memoria
            modelo = np.frombuffer(MODELO.read_bytes(), np.uint8)
            self._det = cv2.FaceDetectorYN.create("onnx", modelo, np.array([], np.uint8), (w, h), self.confianca)
        self._det.setInputSize((w, h))
        _, faces = self._det.detect(quadro_bgr)
        if faces is None or not len(faces):
            return None
        x, y, fw, fh = max(faces, key=lambda f: f[2] * f[3])[:4]
        return float(x), float(y), float(x + fw), float(y + fh)


class TrilhaRosto:
    """Onde a cabeca esta ao longo do video (amostrada a 10 fps e guardada em cache no trabalho).
    cabeca_em(t) junta as caixas de +-janela segundos, para os desenhos nao ficarem pulando."""

    def __init__(self, video, cache, largura=1080, altura=1920, fps_amostra=10, janela=0.3):
        import json
        self.janela = janela
        if cache.exists():
            dados = json.loads(cache.read_text(encoding="utf-8"))
        else:
            cap = cv2.VideoCapture(str(video))
            fps = cap.get(cv2.CAP_PROP_FPS) or 30
            passo = max(1, round(fps / fps_amostra))
            det, dados, n = DetectorRosto(), [], 0
            while True:
                ok = cap.grab()
                if not ok:
                    break
                if n % passo == 0:
                    _, img = cap.retrieve()
                    r = det.achar(img)
                    if r:  # mesma conta do render: amplia ate cobrir 9:16 e corta o centro
                        k = max(largura / img.shape[1], altura / img.shape[0])
                        ox, oy = (img.shape[1] * k - largura) / 2, (img.shape[0] * k - altura) / 2
                        caixa = (r[0] * k - ox, r[1] * k - oy, r[2] * k - ox, r[3] * k - oy)
                        dados.append([round(n / fps, 3)] + [round(v, 1) for v in cabeca(caixa)])
                n += 1
            cap.release()
            cache.write_text(json.dumps(dados), encoding="utf-8")
        self.amostras = dados

    def cabeca_em(self, t):
        perto = [a[1:] for a in self.amostras if abs(a[0] - t) <= self.janela]
        if not perto and self.amostras:
            perto = [min(self.amostras, key=lambda a: abs(a[0] - t))[1:]]
        if not perto:
            return None
        return (min(p[0] for p in perto), min(p[1] for p in perto), max(p[2] for p in perto), max(p[3] for p in perto))


def cabeca(rosto):
    """Area a proteger: o rosto mais a testa em cima e um pouco de queixo (margens do estilo.json)."""
    m = ESTILO["rosto"]
    x0, y0, x1, y1 = rosto
    w, h = x1 - x0, y1 - y0
    return x0 - w * m["margem_lado"], y0 - h * m["margem_topo"], x1 + w * m["margem_lado"], y1 + h * m["margem_baixo"]
