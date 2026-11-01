"""Render: monta cada quadro (video + desenhos + legenda + transicao) e manda direto para o ffmpeg por pipe.

Nenhum quadro e salvo em disco: o Python le o video bruto por um pipe do ffmpeg, desenha por cima
e escreve em outro pipe do ffmpeg, que ja gera o MP4 com o audio mixado.
"""
import subprocess
import sys
import time

from PIL import Image, ImageDraw

from motor import transicoes
from motor.ambiente import RAIZ, achar_ffmpeg
from motor.audio import info_midia
from motor.cenas import Filme
from motor.estilo import ESTILO, cor, fonte
from motor import legenda as legenda_mod
from motor.numero import NumerosAtras
from motor.recorte import TrilhaRecorte
from motor.roteiro import carregar
from motor.rosto import TrilhaRosto
from motor import som

QW, QH, FPS = ESTILO["quadro"]["largura"], ESTILO["quadro"]["altura"], ESTILO["quadro"]["fps"]
SAIDA = ESTILO["saida"]


def _filtro_9x16(largura, altura):
    """Amplia ate cobrir o quadro vertical e corta o centro (video horizontal tambem funciona)."""
    return f"scale={largura}:{altura}:force_original_aspect_ratio=increase:flags=lanczos,crop={largura}:{altura}"


def ler_quadros(video, inicio=0.0, duracao=None, largura=QW, altura=QH, fps=FPS):
    """Gera os quadros do video (PIL RGB) ja no tamanho do Reel, lidos por pipe."""
    cmd = [achar_ffmpeg(), "-v", "error", "-ss", f"{inicio:.3f}", "-i", str(video)]
    if duracao:
        cmd += ["-t", f"{duracao:.3f}"]
    cmd += ["-vf", f"{_filtro_9x16(largura, altura)},fps={fps}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, bufsize=10 ** 8)
    tam = largura * altura * 3
    try:
        while True:
            buf = proc.stdout.read(tam)
            if len(buf) < tam:
                break
            yield Image.frombuffer("RGB", (largura, altura), buf, "raw", "RGB", 0, 1)
    finally:
        proc.stdout.close()
        proc.wait()


def um_quadro(video, t):
    cmd = [achar_ffmpeg(), "-v", "error", "-ss", f"{t:.3f}", "-i", str(video), "-frames:v", "1",
           "-vf", _filtro_9x16(QW, QH), "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
    buf = subprocess.run(cmd, capture_output=True, check=True).stdout
    if len(buf) < QW * QH * 3:  # pediu depois do ultimo quadro: pega um pouco antes
        return um_quadro(video, max(0.0, t - 0.1)) if t > 0.1 else Image.new("RGB", (QW, QH))
    return Image.frombuffer("RGB", (QW, QH), buf[:QW * QH * 3], "raw", "RGB", 0, 1)


def camera(q, zoom, dx, dy):
    """Zoom a partir do centro + deslocamento (tremida). zoom >= 1, entao nunca aparece borda."""
    w, h = round(QW * zoom), round(QH * zoom)
    grande = q.resize((w, h), Image.BICUBIC)
    x0 = min(max(0, (w - QW) / 2 - dx), w - QW)
    y0 = min(max(0, (h - QH) / 2 - dy), h - QH)
    return grande.crop((round(x0), round(y0), round(x0) + QW, round(y0) + QH))


def pagina_de_caderno():
    """Fundo para quando a entrada e so audio: uma folha de caderno nas cores do estilo."""
    img = Image.new("RGB", (QW, QH), cor("fundo")[:3])
    d = ImageDraw.Draw(img)
    for y in range(300, QH, 64):
        d.line([(0, y), (QW, y)], fill=cor("pauta")[:3], width=2)
    d.line([(96, 0), (96, QH)], fill=cor("destaque")[:3], width=3)
    return img


class Motor:
    def __init__(self, trabalho):
        self.pasta, self.roteiro, self.palavras, _ = carregar(trabalho)
        self.trabalho = trabalho
        self.video = RAIZ / self.roteiro["fonte"]
        self.tem_video = info_midia(self.video)["tem_video"]
        self.papel = None if self.tem_video else pagina_de_caderno()
        self.trilha = TrilhaRosto(self.video, self.pasta / "rosto.json") if self.tem_video else None
        self.filme = Filme(self.roteiro, self.palavras, self.trilha)
        chaves = [c["chave"] for c in self.roteiro["cenas"]]
        self.legenda = legenda_mod.criar(self.palavras, chaves, self.roteiro.get("opcoes", {}))
        self.inicio, self.fim = self.roteiro["inicio"], self.roteiro["fim"]
        numeros = self.roteiro.get("opcoes", {}).get("numeros_atras")
        self.numeros = None
        if numeros and self.tem_video:
            recorte = TrilhaRecorte(self.video, self.pasta / "recorte.npz", FPS)
            self.numeros = NumerosAtras(numeros, self.trilha, recorte, self.fim, self.filme.transicoes)
            self.filme.obstaculos_extra = self.numeros.caixas()
            self.filme._layout()  # refaz o layout ja desviando dos numeros

    def quadro(self, fundo, t):
        """Monta o quadro do instante t sobre o quadro do video."""
        q = fundo.convert("RGBA")
        if self.numeros:
            self.numeros.desenhar(q, fundo, t)
        self.filme.cena_em(t).desenhar(q, t)
        z, dx, dy = self.filme.camera(t)
        if z > 1.0005 or abs(dx) > 0.5 or abs(dy) > 0.5:
            q = camera(q, z, dx, dy)
        self.legenda.desenhar(q, t)
        for tr in self.filme.transicoes:
            if tr["inicio"] < t < tr["fim"]:
                transicoes.desenhar(q, (t - tr["inicio"]) / (tr["fim"] - tr["inicio"]), semente=tr["capitulo"])
        return q

    # ---------- audio ----------
    def preparar_audio(self, inicio=None, duracao=None):
        voz = som.ler_audio(self.video)
        eventos = som.eventos_do_filme(self.filme)
        if self.numeros:
            eventos = sorted(eventos + self.numeros.gatilhos())
        eventos = som.filtrar(eventos, self.roteiro.get("opcoes", {}))
        faixa = som.faixa_de_efeitos(eventos, len(voz) / som.TAXA, voz)
        efeitos = self.pasta / "efeitos.wav"
        som.salvar_wav(efeitos, faixa)
        mix = self.pasta / ("audio_final.wav" if inicio is None else "audio_trecho.wav")
        lufs_antes = som.mixar(self.video, efeitos, mix, inicio or self.inicio, duracao or (self.fim - self.inicio))
        return mix, eventos, lufs_antes

    # ---------- video completo ----------
    def renderizar(self, inicio=None, fim=None, largura=QW, altura=QH, nome=None, crf=None, preset=None):
        inicio = self.inicio if inicio is None else inicio
        fim = self.fim if fim is None else fim
        saida_dir = self.pasta / "saida"
        saida_dir.mkdir(exist_ok=True)
        arquivo = saida_dir / (nome or f"{self.trabalho}_1080x1920.mp4")
        audio, eventos, lufs = self.preparar_audio(None if (inicio, fim) == (self.inicio, self.fim) else inicio, fim - inicio)
        v = SAIDA["video"]
        cmd = [achar_ffmpeg(), "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{QW}x{QH}", "-r", str(FPS),
               "-i", "-", "-i", str(audio), "-map", "0:v", "-map", "1:a"]
        if (largura, altura) != (QW, QH):
            cmd += ["-vf", f"scale={largura}:{altura}:flags=lanczos"]
        cmd += ["-c:v", v["codec"], "-preset", preset or v["preset"], "-crf", str(crf or v["crf"]), "-pix_fmt", v["pix_fmt"],
                "-c:a", SAIDA["audio"]["codec"], "-b:a", SAIDA["audio"]["bitrate"], "-movflags", "+faststart", "-shortest", str(arquivo)]
        enc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
        total = round((fim - inicio) * FPS)
        t0 = time.time()
        fundos = ler_quadros(self.video, inicio, fim - inicio) if self.tem_video else (self.papel for _ in range(total))
        for n, fundo in enumerate(fundos):
            if n >= total:
                break
            t = inicio + n / FPS
            enc.stdin.write(self.quadro(fundo, t).convert("RGB").tobytes())
            if n % (FPS * 3) == 0 and n:
                gasto = time.time() - t0
                print(f"  {t:5.1f}s de {fim:.1f}s · {n / gasto:4.1f} quadros/s · faltam ~{(total - n) / (n / gasto):.0f}s", flush=True)
        enc.stdin.close()
        enc.wait()
        return arquivo, len(eventos), lufs, time.time() - t0

    def versao_leve(self, arquivo):
        leve = SAIDA["versao_leve"]
        destino = arquivo.with_name(arquivo.stem.replace("1080x1920", "") .rstrip("_") + "_celular.mp4")
        subprocess.run([achar_ffmpeg(), "-y", "-v", "error", "-i", str(arquivo), "-vf", f"scale={leve['largura']}:{leve['altura']}:flags=lanczos",
                        "-c:v", "libx264", "-preset", "medium", "-crf", str(leve["crf"]), "-pix_fmt", "yuv420p",
                        "-c:a", "aac", "-b:a", leve["audio_bitrate"], "-movflags", "+faststart", str(destino)], check=True)
        return destino

    # ---------- previa ----------
    def instantes_padrao(self):
        """Um instante por cena (logo depois do impacto da palavra-chave) + o meio de cada transicao."""
        ts = []
        for c in self.roteiro["cenas"]:
            p = self.palavras[c["chave"]]
            ts.append((round(min(p["inicio"] + 0.4, self.fim - 0.1), 2), c["id"]))
        ts += [(round((tr["inicio"] + tr["fim"]) / 2, 2), f"transição #{tr['capitulo']}") for tr in self.filme.transicoes[:1] if not tr.get("corte")]
        return sorted(ts)

    def previa(self, instantes=None, guias=False, colunas=5, escala=0.3):
        """Folha de contato com os instantes pedidos (sem renderizar o video inteiro)."""
        instantes = instantes or self.instantes_padrao()
        w, h = round(QW * escala), round(QH * escala)
        rot_h = 54
        linhas = -(-len(instantes) // colunas)
        folha = Image.new("RGB", (colunas * (w + 16) + 16, linhas * (h + rot_h + 16) + 16), (27, 27, 29))
        d = ImageDraw.Draw(folha)
        quadros = []
        for i, (t, rotulo) in enumerate(instantes):
            q = self.quadro(um_quadro(self.video, t) if self.tem_video else self.papel, t)
            if guias:
                q = self.desenhar_guias(q, t)
            quadros.append((t, rotulo, q))
            x, y = 16 + (i % colunas) * (w + 16), 16 + (i // colunas) * (h + rot_h + 16)
            folha.paste(q.convert("RGB").resize((w, h), Image.LANCZOS), (x, y))
            cena = self.filme.cena_em(t)
            d.text((x, y + h + 6), f"{rotulo} · {t:.2f}s", font=fonte("anotacao", 20), fill=(240, 240, 240))
            frase = " ".join(p["texto"] for p in self.palavras if cena.inicio <= p["inicio"] < cena.fim)
            d.text((x, y + h + 30), (frase[:38] + "…") if len(frase) > 39 else frase, font=fonte("anotacao", 15), fill=(170, 170, 175))
        return folha, quadros

    def desenhar_guias(self, q, t):
        """Areas seguras do Reels, rosto protegido e caixa da legenda (para revisao)."""
        q = q.copy()
        cam = Image.new("RGBA", q.size)
        d = ImageDraw.Draw(cam)
        seg = ESTILO["areas_seguras"]
        vermelho = (230, 40, 60, 70)
        d.rectangle([0, 0, QW, seg["topo"]], fill=vermelho)
        d.rectangle([0, QH - seg["base"], QW, QH], fill=vermelho)
        d.rectangle([QW - seg["direita"], 1000, QW, QH], fill=vermelho)
        cab = self.trilha.cabeca_em(t) if self.trilha else None
        if cab:
            d.rectangle(cab, outline=(40, 200, 255, 255), width=4)
        q.alpha_composite(cam)
        return q
