"""Faz o Reel inteiro com um comando: transcreve, monta o rascunho do roteiro, deixa voce revisar,
confere tudo sozinho e renderiza.

Uso:
  .venv\\Scripts\\python fazer_video.py meu_video.mp4
  .venv\\Scripts\\python fazer_video.py meu_audio.m4a --chamada "me segue pra mais!"

Opcoes:
  --nome NOME            pasta do trabalho em trabalhos\\ (padrao: nome do arquivo)
  --contador "parte #{n}" escreve um contador no canto a cada capitulo ({n} vira o numero)
  --chamada "TEXTO"      cena final "chamada para seguir" com esse texto
  --dica "PALAVRAS"      palavras dificeis do assunto, para a transcricao acertar
  --cobrir-legenda       o video ja tem legenda gravada na imagem: a nossa fica sempre por cima
  --refazer              transcreve e monta o roteiro de novo (apaga as revisoes feitas)
  --refazer-roteiro      so monta um novo rascunho do roteiro (mantem a transcricao corrigida)
  --so-previa            para depois da folha de contato (nao renderiza o video)
  --sem-pausas           nao espera Enter entre as etapas
"""
import argparse
import json
import sys
import time
from pathlib import Path

from motor.ambiente import RAIZ
from motor.audio import info_midia
from motor.transcricao import MODELO_PADRAO, aplicar_revisao, gerar_revisao, salvar_json, transcrever


def etapa(n, texto):
    print(f"\n━━ {n}/5 · {texto}")


def pausar(args, pergunta):
    if args.sem_pausas:
        return
    try:
        input(f"\n   {pergunta} [Enter para continuar, Ctrl+C para parar] ")
    except KeyboardInterrupt:
        print("\nParado. Rode o mesmo comando de novo para continuar de onde parou.")
        sys.exit(0)


def caminho_relativo(p: Path) -> str:
    try:
        return str(p.resolve().relative_to(RAIZ)).replace("\\", "/")
    except ValueError:
        return str(p.resolve())


def main():
    ap = argparse.ArgumentParser(description="Transforma um video ou audio falado em Reel animado.")
    ap.add_argument("arquivo")
    ap.add_argument("--nome")
    ap.add_argument("--contador")
    ap.add_argument("--chamada")
    ap.add_argument("--dica")
    ap.add_argument("--modelo", default=MODELO_PADRAO, help="modelo de transcricao")
    ap.add_argument("--cobrir-legenda", action="store_true")
    ap.add_argument("--refazer", action="store_true")
    ap.add_argument("--refazer-roteiro", action="store_true")
    ap.add_argument("--so-previa", action="store_true")
    ap.add_argument("--sem-pausas", action="store_true")
    args = ap.parse_args()

    entrada = Path(args.arquivo)
    if not entrada.exists():
        sys.exit(f"Nao achei o arquivo: {entrada}")
    nome = args.nome or entrada.stem
    pasta = RAIZ / "trabalhos" / nome
    pasta.mkdir(parents=True, exist_ok=True)
    midia = info_midia(entrada)
    print(f"Trabalho: {nome} · {'video' if midia['tem_video'] else 'so audio'} · {midia['duracao']:.1f}s")
    if midia["duracao"] > 75:
        print("   Aviso: passa de 1 minuto. O Reel fica com a duracao do arquivo.")

    # 1. transcricao + revisao do texto
    etapa(1, "Transcricao")
    original, revisao, final = pasta / "palavras_original.json", pasta / "revisao.txt", pasta / "palavras.json"
    if args.refazer or not original.exists():
        print("   Transcrevendo (na primeira vez o modelo e baixado)...")
        dados = transcrever(entrada, pasta, args.modelo, dica=args.dica)
        salvar_json(original, dados)
        revisao.write_text(gerar_revisao(dados), encoding="utf-8")
        print(f"   {len(dados['palavras'])} palavras em {dados['tempo_processamento']}s ({dados['modelo']}, {dados['dispositivo']})")
    else:
        print("   Ja transcrito antes (use --refazer para transcrever de novo).")
    print("\n" + revisao.read_text(encoding="utf-8"))
    print(f"   Para corrigir palavras: edite {revisao} e salve.")
    pausar(args, "Texto revisado?")
    dados = aplicar_revisao(json.loads(original.read_text(encoding="utf-8")), revisao.read_text(encoding="utf-8"))
    salvar_json(final, dados)
    P = dados["palavras"]
    editadas = [p["texto"] for p in P if p.get("editada")]
    if editadas:
        print(f"   Correcoes aplicadas: {', '.join(editadas)}")

    # 2. rascunho do roteiro
    etapa(2, "Roteiro de cenas")
    from motor.rascunho import gerar
    from motor.roteiro import carregar, tabela_md, validar
    roteiro_json = pasta / "roteiro.json"
    if args.refazer or args.refazer_roteiro or not roteiro_json.exists():
        inicio = max(0.0, P[0]["inicio"] - 0.15) if P[0]["inicio"] > 0.4 else 0.0
        fim = min(midia["duracao"], P[-1]["fim"] + 0.9)
        if inicio:
            print(f"   Cortando {inicio:.2f}s de silencio do comeco.")
        rot = gerar(P, caminho_relativo(entrada), inicio, fim, midia["tem_video"], args.contador, args.chamada, args.cobrir_legenda)
        rot["trabalho"] = nome
        roteiro_json.write_text(json.dumps(rot, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"   Rascunho criado: {len(rot['cenas'])} cenas, {len(rot['capitulos'])} capitulo(s).")
    else:
        print("   Usando o roteiro.json que ja existe (use --refazer para gerar um novo rascunho).")
    while True:
        _, rot, P, estilo = carregar(nome)
        erros, avisos, info = validar(rot, P, estilo)
        (pasta / "roteiro.md").write_text(f"# Roteiro de cenas · {nome}\n\n" + tabela_md(rot, P, estilo), encoding="utf-8")
        print(f"   Tabela para revisar: {pasta / 'roteiro.md'}  (mude o que quiser em {roteiro_json})")
        for e in erros:
            print("   ERRO:", e)
        for a in avisos:
            print("   aviso:", a)
        if not erros:
            break
        if args.sem_pausas:
            sys.exit("Corrija os erros do roteiro e rode de novo.")
        pausar(args, "Corrija o roteiro.json e salve.")
    pausar(args, "Roteiro aprovado?")

    # 3. revisao automatica + previa
    etapa(3, "Revisao automatica e previa")
    from motor import revisao as rev
    from motor.render import Motor
    motor = Motor(nome)
    problemas = rev.revisar_layout(motor)
    for (regra, quem), ts in sorted(problemas.items(), key=lambda x: x[1][0]):
        print(f"   [{regra}] {quem}: {', '.join(rev.agrupar(ts, 1 / 15)[:6])}")
    leitura, menor = rev.revisar_leitura(motor)
    for x in leitura:
        print("   [leitura]", x)
    vaz = rev.revisar_pixels(motor) if args.cobrir_legenda or rot.get("opcoes", {}).get("cobrir_legenda_antiga") else []
    for t, o_que, n in vaz:
        print(f"   [vazamento] {o_que} em {t}s")
    folha, _ = motor.previa()
    folha.save(pasta / "previa.png")
    print(f"   {len(problemas) + len(leitura) + len(vaz)} ponto(s) para olhar · menor letra da legenda {menor}px")
    print(f"   Folha de contato: {pasta / 'previa.png'}")
    if args.so_previa:
        print("\nPronto (so previa). Para renderizar: rode de novo sem --so-previa.")
        return
    pausar(args, "Previa aprovada? O proximo passo renderiza o video completo.")

    # 4. render completo
    etapa(4, "Render")
    t0 = time.time()
    arquivo, n_sons, lufs, gasto = motor.renderizar()
    print(f"   Video: {arquivo} ({gasto:.0f}s, {n_sons} efeitos, volume {lufs:.1f} -> -14 LUFS)")

    # 5. versao leve
    etapa(5, "Versao para celular")
    leve = motor.versao_leve(arquivo)
    print(f"   {leve}")
    print(f"\nPronto em {(time.time() - t0) / 60:.1f} min. Arquivos em {pasta / 'saida'}")


if __name__ == "__main__":
    main()
