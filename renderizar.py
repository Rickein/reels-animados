"""Renderiza o Reel de um trabalho (ou so uma previa).

Uso:
  .venv\\Scripts\\python renderizar.py verdades-magreza --previa            folha de contato (1 quadro por cena)
  .venv\\Scripts\\python renderizar.py verdades-magreza --previa --guias    idem, com areas seguras e rosto marcados
  .venv\\Scripts\\python renderizar.py verdades-magreza --previa --tempos 3.5,17.6
  .venv\\Scripts\\python renderizar.py verdades-magreza --trecho 12-19      video curto e leve de um trecho
  .venv\\Scripts\\python renderizar.py verdades-magreza                     video completo + versao para celular
"""
import argparse
import time

from motor.render import Motor


def main():
    ap = argparse.ArgumentParser(description="Renderiza o Reel a partir do roteiro.")
    ap.add_argument("trabalho")
    ap.add_argument("--previa", action="store_true")
    ap.add_argument("--guias", action="store_true", help="marca areas seguras e rosto na previa")
    ap.add_argument("--tempos", help="instantes da previa, separados por virgula (s)")
    ap.add_argument("--trecho", help="renderiza so um trecho, ex.: 12-19")
    ap.add_argument("--revisar", action="store_true", help="confere as regras no video inteiro, sem renderizar")
    ap.add_argument("--pixels", action="store_true", help="na revisao, confere tambem a legenda antiga nos pixels (mais lento)")
    a = ap.parse_args()

    t0 = time.time()
    motor = Motor(a.trabalho)
    print(f"Motor pronto em {time.time() - t0:.1f}s ({len(motor.filme.cenas)} cenas, {len(motor.filme.atores)} desenhos)")

    if a.revisar:
        from motor import revisao
        problemas = revisao.revisar_layout(motor)
        for (regra, quem), ts in sorted(problemas.items(), key=lambda x: x[1][0]):
            print(f"  [{regra}] {quem}: {', '.join(revisao.agrupar(ts, 1 / 15))}")
        avisos, menor = revisao.revisar_leitura(motor)
        for x in avisos:
            print("  [leitura]", x)
        atraso, fora = revisao.revisar_sincronia(motor)
        for x in fora:
            print("  [sincronia]", x)
        vaz = revisao.revisar_pixels(motor) if a.pixels else []
        for t, o_que, n in vaz:
            print(f"  [vazamento] {o_que} aparecendo em {t}s ({n} px)")
        total = len(problemas) + len(avisos) + len(fora) + len(vaz)
        print(f"Legenda: menor letra {menor}px · maior atraso combinado {atraso:.2f}s · "
              f"{'pixels conferidos' if a.pixels else 'pixels nao conferidos'} · {total} problema(s)")
        return

    if a.previa:
        tempos = [(float(x), f"{float(x):.2f}s") for x in a.tempos.split(",")] if a.tempos else None
        folha, _ = motor.previa(tempos, guias=a.guias)
        nome = "previa_guias.png" if a.guias else "previa.png"
        folha.save(motor.pasta / nome)
        print(f"Previa: {motor.pasta / nome}")
        return

    if a.trecho:
        ini, fim = (float(x) for x in a.trecho.split("-"))
        arquivo, n_sons, lufs, gasto = motor.renderizar(ini, fim, 540, 960, nome=f"trecho_{ini:g}-{fim:g}.mp4", crf=24, preset="veryfast")
        print(f"Trecho: {arquivo} ({gasto:.0f}s, {n_sons} sons)")
        return

    arquivo, n_sons, lufs, gasto = motor.renderizar()
    print(f"Video: {arquivo} ({gasto:.0f}s de render, {n_sons} efeitos sonoros, volume original {lufs:.1f} LUFS -> -14)")
    leve = motor.versao_leve(arquivo)
    print(f"Versao para celular: {leve}")


if __name__ == "__main__":
    main()
