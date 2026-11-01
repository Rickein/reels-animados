"""Valida o roteiro de cenas e gera a tabela legivel (roteiro.md).

Uso:  .venv\\Scripts\\python ver_roteiro.py verdades-magreza
"""
import sys

from motor.roteiro import carregar, tabela_md, validar


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    pasta, roteiro, palavras, estilo = carregar(sys.argv[1])
    erros, avisos, info = validar(roteiro, palavras, estilo)
    tabela = tabela_md(roteiro, palavras, estilo)
    (pasta / "roteiro.md").write_text(f"# Roteiro de cenas · {roteiro['trabalho']}\n\n" + tabela, encoding="utf-8")

    print(f"{len(roteiro['cenas'])} cenas · {len(roteiro['elementos'])} elementos · "
          f"maior tempo sem movimento: {info['maior_parada']}s")
    print("Transicoes:", ", ".join(f"#{t['capitulo']} {t['inicio']:.2f}–{t['fim']:.2f}s" for t in info["transicoes"]))
    for e in erros:
        print("ERRO:", e)
    for a in avisos:
        print("aviso:", a)
    print("Tabela salva em", pasta / "roteiro.md")
    sys.exit(1 if erros else 0)


if __name__ == "__main__":
    main()
