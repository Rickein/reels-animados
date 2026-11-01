"""Desenha a biblioteca inteira: um PNG por elemento, um catalogo e um teste de leitura sobre o video.

Uso:  .venv\\Scripts\\python montar_biblioteca.py [video_para_teste]
Saida: biblioteca\\png\\*.png, biblioteca\\catalogo.png, biblioteca\\teste_sobre_video.png
"""
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw

from motor.ambiente import RAIZ
from motor.biblioteca import REGISTRO, obter
from motor.estilo import ESTILO, cor, fonte, zona
from motor.rosto import DetectorRosto, cabeca

PASTA = RAIZ / "biblioteca"

# (rotulo, desenho, parametros) — inclui os estados que as animacoes vao usar
CATALOGO = [
    ("cartao papel", "cartao_papel", {"largura": 300, "altura": 110}), ("cronômetro", "cronometro", {"ponteiro": 1.2}),
    ("texto à mão", "texto_mao", {"texto": "40s"}), ("contador", "contador", {"texto": "verdade #3", "concluido": True}),
    ("fita métrica", "fita_metrica", {}), ("fita em espiral", "fita_metrica", {"espiral": 1.0}),
    ("gotas de suor", "gotas_suor", {"n": 3}), ("gotas ×6", "gotas_suor", {"n": 6}),
    ("espelho", "espelho", {}), ("espelho espremido", "espelho", {"espremer": 1.0}),
    ("seta subindo", "seta_subindo", {}), ("seta curva", "seta", {}),
    ("celular", "celular", {}), ("prato de salada", "prato_salada", {}),
    ("coração", "coracao", {}), ("curtidas", "coracoes", {}),
    ("wi-fi", "wifi", {}), ("megafone gritando", "megafone", {"ondas": 1.0}),
    ("balança", "balanca", {"inclinacao": -0.3, "coracao": True}), ("borrifador", "borrifador", {"borrifo": 1.0}),
    ("pão com medo", "pao", {"suor": 2}), ("pão francês de boina", "pao", {"tipo": "frances", "boina": True}),
    ("ring light", "ring_light", {"brilho": 1.0}), ("etiqueta", "etiqueta_preco", {"texto": "5 kg"}),
    ("lista de tarefas", "lista_tarefas", {"comprimento": 1.4}), ("tênis", "tenis", {}),
    ("halter", "halter", {}), ("tapete de yoga", "tapete_yoga", {}),
    ("balão de pensamento", "balao_pensamento", {}), ("relógio de ponto", "relogio_ponto", {}),
    ("crachá", "cracha", {}), ("sol", "sol", {}),
    ("ondas", "ondas", {}), ("guarda-sol", "guarda_sol", {}),
    ("binóculos", "binoculos", {}), ("transferidor", "transferidor", {}),
    ("lupa", "lupa", {}), ("bíceps", "biceps", {"brilho": 1.0}),
    ("fábrica", "fabrica", {"fumaca": 1.0}), ("lâmpada acesa", "lampada", {"acesa": 1.0}),
    ("selo", "selo", {}), ("cifrões", "cifroes", {}),
    ("sacola", "sacola", {}), ("garrafa d'água", "garrafa_agua", {}),
    ("círculo rabiscado", "circulo", {}), ("check / xis", "check", {}),
    ("casa", "casa", {}), ("gráfico", "grafico", {}),
    ("balão de fala", "balao_fala", {}), ("dinheiro", "dinheiro", {}),
]


def caber(img, largura, altura):
    k = min(1.0, largura / img.width, altura / img.height)
    return img if k >= 1 else img.resize((round(img.width * k), round(img.height * k)), Image.LANCZOS)


def montar_catalogo():
    (PASTA / "png").mkdir(parents=True, exist_ok=True)
    col, cel_w, cel_h = 6, 320, 330
    lin = -(-len(CATALOGO) // col)
    folha = Image.new("RGBA", (col * cel_w, lin * cel_h + 90), (201, 198, 195, 255))  # cinza parecido com a parede do video
    d = ImageDraw.Draw(folha)
    d.text((24, 26), "Biblioteca · Correção a Caneta · Ameixa", font=fonte("titulo", 40), fill=cor("principal"))
    for i, (rotulo, nome, params) in enumerate(CATALOGO):
        img, _ = obter(nome, **params)
        sufixo = "_" + "_".join(f"{k}-{v}" for k, v in params.items() if k not in ("texto",)) if params else ""
        img.save(PASTA / "png" / f"{nome}{sufixo}.png")
        x, y = (i % col) * cel_w, 90 + (i // col) * cel_h
        peq = caber(img, cel_w - 30, cel_h - 64)
        folha.alpha_composite(peq, (x + (cel_w - peq.width) // 2, y + 10 + (cel_h - 64 - peq.height) // 2))
        d.text((x + cel_w // 2, y + cel_h - 30), rotulo, font=fonte("anotacao", 24), fill=cor("texto"), anchor="mm")
    folha.convert("RGB").save(PASTA / "catalogo.png")
    faltando = sorted(set(REGISTRO) - {n for _, n, _ in CATALOGO})
    return len(CATALOGO), faltando


def quadro_do_video(video, t):
    cap = cv2.VideoCapture(str(video))
    cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
    ok, img = cap.read()
    cap.release()
    img = cv2.resize(cv2.cvtColor(img, cv2.COLOR_BGR2RGB), (1080, 1920), interpolation=cv2.INTER_CUBIC)
    return Image.fromarray(img).convert("RGBA")


def colocar(quadro, nome, zona_nome=None, centro=None, escala=1.0, slot=(0, 1), **params):
    """Coloca um desenho preenchendo uma zona (ou uma fatia dela, com slot=(i, n)), ou num ponto exato."""
    if zona_nome:
        x0, y0, x1, y1 = zona(zona_nome)
        i, n = slot
        x0, x1 = x0 + (x1 - x0) * i / n, x0 + (x1 - x0) * (i + 1) / n
        z = ESTILO["zonas"]
        img, _ = obter(nome, **params)
        k = min((x1 - x0) * z["preenchimento"] / img.width, (y1 - y0) * z["preenchimento"] / img.height, z["ampliacao_max"])
        img, _ = obter(nome, escala=k, **params)
        quadro.alpha_composite(img, (round((x0 + x1 - img.width) / 2), round((y0 + y1 - img.height) / 2)))
        return (round((x0 + x1 - img.width) / 2), round((y0 + y1 - img.height) / 2), img.width, img.height)
    img, (ox, oy) = obter(nome, escala=escala, **params)
    quadro.alpha_composite(img, (round(centro[0] - ox), round(centro[1] - oy)))
    return (round(centro[0] - ox), round(centro[1] - oy), img.width, img.height)


def teste_sobre_video(video):
    detector = DetectorRosto()
    cenas, avisos = [], []

    def checar_rosto(q, t, caixas):
        quadro_bgr = cv2.cvtColor(np.array(q.convert("RGB")), cv2.COLOR_RGB2BGR)
        r = detector.achar(quadro_bgr)
        if not r:
            return
        hx0, hy0, hx1, hy1 = cabeca(r)
        for nome, (x, y, w, h) in caixas.items():
            if x < hx1 and x + w > hx0 and y < hy1 and y + h > hy0:
                avisos.append(f"{t}s: {nome} encosta no rosto")

    q = quadro_do_video(video, 17.0)  # C06: balanca
    cx = {"balanca": colocar(q, "balanca", "lado_direito", inclinacao=-0.3, coracao=True)}
    colocar(q, "contador", centro=(60, 310), texto="verdade #2")
    checar_rosto(quadro_do_video(video, 17.0), 17.0, cx)
    cenas.append(q)
    q = quadro_do_video(video, 24.2)  # C08: pao frances
    colocar(q, "contador", centro=(60, 310), texto="verdade #3")
    cx = {"texto": colocar(q, "texto_mao", "topo_direito", texto="“alimentação limpa”", tamanho=52, rotacao=-4),
          "pao": colocar(q, "pao", "lado_direito", tipo="frances", boina=True, suor=2)}
    checar_rosto(quadro_do_video(video, 24.2), 24.2, cx)
    cenas.append(q)
    q = quadro_do_video(video, 33.9)  # C12: CLT
    colocar(q, "contador", centro=(60, 310), texto="verdade #4")
    cx = {"relogio": colocar(q, "relogio_ponto", "lado_direito"),
          "tenis": colocar(q, "tenis", "lado_esquerdo", slot=(0, 1)),
          "cracha": colocar(q, "cracha", "peito_direito")}
    colocar(q, "halter", "peito_esquerdo", slot=(0, 2))
    colocar(q, "tapete_yoga", "peito_esquerdo", slot=(1, 2))
    checar_rosto(quadro_do_video(video, 33.9), 33.9, cx)
    cenas.append(q)
    for a in avisos:
        print("aviso:", a)
    folha = Image.new("RGBA", (3 * 1080 + 80, 1920 + 40), (27, 27, 29, 255))
    for i, q in enumerate(cenas):
        folha.alpha_composite(q, (20 + i * 1100, 20))
    folha.convert("RGB").resize((folha.width // 2, folha.height // 2), Image.LANCZOS).save(PASTA / "teste_sobre_video.png")


def demo_animada(segundos=4.0, fps=30):
    """Video curto 1080x1080: cada desenho se desenha e depois 'ferve' e muda de estado (a 12 fps, como o estilo)."""
    import subprocess
    from motor.ambiente import achar_ffmpeg
    fps_desenho = ESTILO["movimento"]["fps_desenhos"]
    ciclo = ESTILO["traco"]["fervura"]["desenhos_no_ciclo"]
    clamp = lambda x: max(0.0, min(1.0, x))
    celulas = [
        ("pao", lambda u: {"tipo": "frances" if u > 0.5 else "forma", "boina": u > 0.75, "suor": 2 if u > 0.25 else 0}),
        ("balanca", lambda u: {"inclinacao": -0.35 * u, "coracao": True}),
        ("wifi", lambda u: {}),
        ("megafone", lambda u: {"ondas": u}),
        ("fita_metrica", lambda u: {"espiral": u}),
        ("lampada", lambda u: {"acesa": u}),
        ("espelho", lambda u: {"espremer": u}),
        ("contador", lambda u: {"texto": "verdade #7", "concluido": u > 0.6}),
        ("selo", lambda u: {}),
    ]
    saida = PASTA / "demo_animacao.mp4"
    cmd = [achar_ffmpeg(), "-y", "-hide_banner", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
           "-s", "1080x1080", "-r", str(fps), "-i", "-", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20", str(saida)]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for f in range(round(segundos * fps)):
        t = f / fps
        td = int(t * fps_desenho) / fps_desenho          # desenhos andam "em dois" (12 fps)
        quadro = Image.new("RGBA", (1080, 1080), (201, 198, 195, 255))
        for i, (nome, estado) in enumerate(celulas):
            atraso = 0.12 * i
            prog = clamp((td - atraso) / 0.8)
            if prog <= 0:
                continue
            u = clamp((td - 1.4 - atraso * 0.5) / 1.2)
            img, _ = obter(nome, semente=int(td * fps_desenho) % ciclo, progresso=round(prog, 2), **estado(u))
            img = caber(img, 330, 330)
            cx, cy = 180 + (i % 3) * 360, 180 + (i // 3) * 360
            quadro.alpha_composite(img, (cx - img.width // 2, cy - img.height // 2))
        proc.stdin.write(quadro.convert("RGB").tobytes())
    proc.stdin.close()
    proc.wait()
    return saida


if __name__ == "__main__":
    n, faltando = montar_catalogo()
    print(f"Catalogo: {n} desenhos em {PASTA / 'catalogo.png'}")
    if faltando:
        print("Sem amostra no catalogo:", ", ".join(faltando))
    video = sys.argv[1] if len(sys.argv) > 1 else next((RAIZ / "Bruto").iterdir())
    teste_sobre_video(video)
    print(f"Teste sobre o video: {PASTA / 'teste_sobre_video.png'}")
    print(f"Demo animada: {demo_animada()}")
