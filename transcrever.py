"""Transcreve um audio ou video com o tempo de cada palavra e prepara o texto para revisao.

Uso:
  .venv\\Scripts\\python transcrever.py Bruto\\meu_video.mp4             transcreve
  .venv\\Scripts\\python transcrever.py Bruto\\meu_video.mp4 --aplicar   aplica as correcoes do revisao.txt

Opcoes:
  --nome PASTA      nome da pasta em trabalhos\\ (padrao: nome do arquivo)
  --modelo NOME     large-v3-turbo (padrao, GPU) ou small (CPU)
  --dica "TEXTO"    palavras dificeis do assunto, para ajudar a transcricao
"""
import argparse
import json
import shutil
import sys
from pathlib import Path

from motor.ambiente import RAIZ
from motor.transcricao import MODELO_PADRAO, aplicar_revisao, gerar_revisao, salvar_json, transcrever


def main():
    ap = argparse.ArgumentParser(description="Transcreve com o tempo de cada palavra.")
    ap.add_argument("arquivo", help="audio ou video (m4a, mp3, wav, mp4...)")
    ap.add_argument("--nome", help="nome da pasta do trabalho")
    ap.add_argument("--modelo", default=MODELO_PADRAO)
    ap.add_argument("--dica", help="vocabulario do assunto para ajudar a transcricao")
    ap.add_argument("--aplicar", action="store_true", help="aplica as correcoes feitas no revisao.txt")
    a = ap.parse_args()

    pasta = RAIZ / "trabalhos" / (a.nome or Path(a.arquivo).stem)
    caminho_json, caminho_original, caminho_revisao = pasta / "palavras.json", pasta / "palavras_original.json", pasta / "revisao.txt"

    if a.aplicar:
        if not caminho_original.exists():
            sys.exit(f"Nao achei {caminho_original}. Rode primeiro sem --aplicar.")
        original = json.loads(caminho_original.read_text(encoding="utf-8"))
        dados = aplicar_revisao(original, caminho_revisao.read_text(encoding="utf-8"))
        salvar_json(caminho_json, dados)
        editadas = [p["texto"] for p in dados["palavras"] if p.get("editada")]
        print(f"Correcoes aplicadas ({len(editadas)} palavra(s) ajustada(s)): {', '.join(editadas) or '-'}")
        print(f"Salvo em {caminho_json}")
        return

    if not Path(a.arquivo).exists():
        sys.exit(f"Arquivo nao encontrado: {a.arquivo}")
    print("Transcrevendo (na primeira vez o modelo e baixado, pode demorar)...")
    dados = transcrever(a.arquivo, pasta, a.modelo, dica=a.dica)
    salvar_json(caminho_original, dados)
    shutil.copy(caminho_original, caminho_json)
    caminho_revisao.write_text(gerar_revisao(dados), encoding="utf-8")
    print(f"{len(dados['palavras'])} palavras em {dados['tempo_processamento']}s "
          f"({dados['modelo']} na {dados['dispositivo']}). Primeira palavra em {dados['palavras'][0]['inicio']}s.")
    print(f"Arquivos: {caminho_json}\n          {caminho_revisao}\n")
    print(gerar_revisao(dados))


if __name__ == "__main__":
    main()
