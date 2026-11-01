"""Tempo: progresso, curvas de aceleracao (easing), mola e tremida de camera."""
import math
import random

from motor.estilo import ESTILO

FPS_DESENHO = ESTILO["movimento"]["fps_desenhos"]
CICLO_FERVURA = ESTILO["traco"]["fervura"]["desenhos_no_ciclo"]


def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def progresso(t, inicio, duracao):
    """0 antes de comecar, 1 depois de terminar."""
    return clamp((t - inicio) / duracao) if duracao > 0 else float(t >= inicio)


def ease_out(p):
    return 1 - (1 - p) ** 3


def ease_out_expo(p):
    return 1.0 if p >= 1 else 1 - 2 ** (-10 * p)


def in_out(p):
    return 4 * p ** 3 if p < 0.5 else 1 - (-2 * p + 2) ** 3 / 2


def back_out(p, passada=1.70158):
    """Passa um pouco do ponto e volta (o 'quique' de entrada)."""
    c = passada + 1
    return 1 + c * (p - 1) ** 3 + passada * (p - 1) ** 2


def mola(u, amplitude=1.0, amortecimento=7.0, frequencia=18.0):
    """Oscilacao que morre: u = segundos desde o empurrao. Comeca em 'amplitude' e vai a 0."""
    return 0.0 if u < 0 else amplitude * math.exp(-amortecimento * u) * math.cos(frequencia * u)


def tremida(t, inicio, duracao, amplitude, fps=FPS_DESENHO, semente=17):
    """Deslocamento (dx, dy) que treme 'em dois' e diminui ate parar."""
    if not inicio <= t <= inicio + duracao:
        return 0.0, 0.0
    k = 1 - (t - inicio) / duracao
    r = random.Random(int((t - inicio) * fps) * 7919 + semente)
    return (r.random() * 2 - 1) * amplitude * k, (r.random() * 2 - 1) * amplitude * k


def em_dois(t, fps=FPS_DESENHO):
    """Arredonda o tempo para a cadencia dos desenhos (12 fps): estados mudam 'em dois', como animacao a mao."""
    return math.floor(t * fps + 1e-6) / fps


def fervura(t, deslocamento=0):
    """Qual dos desenhos do ciclo usar agora (a linha 'ferve')."""
    return (int(t * FPS_DESENHO + 1e-6) + deslocamento) % CICLO_FERVURA
