# Projeto: Reels animados por código

Este arquivo é lido automaticamente quando um novo chat do Claude Code abre esta pasta. Ele resume
a metodologia combinada para criar novos vídeos. O manual técnico completo está em `LEIAME.md`.
A mesma metodologia está na skill `.claude/skills/reels-animados/SKILL.md`. Num computador novo, rode `instalar.ps1`.

## O que é

Uma ferramenta que transforma um vídeo de rosto falando (ou só um áudio) num **Reel vertical 1080x1920**
com desenhos à mão animados, legenda palavra por palavra, transições e efeitos sonoros, tudo gerado
por código (Python + Pillow + ffmpeg + faster-whisper), sem editor de vídeo.

Primeiro vídeo feito: `trabalhos/verdades-magreza/` (nutricionista, "7 verdades sobre a pira da magreza").
O resultado final está em `trabalhos/verdades-magreza/saida/verdades-magreza_1080x1920.mp4`.

## Formatos já criados

- **Correção a Caneta**: o padrão, do primeiro vídeo (`trabalhos/verdades-magreza/`). Tem tira de caderno na legenda,
  contador "verdade #n", rabisco entre capítulos e efeitos sonoros em tudo.
- **Take a Take**: lista com um take por item. O número sobe por trás da cabeça, a legenda é limpa e fica lilás,
  os sons são mínimos e os desenhos ficam no centro. Receita completa em `formatos/take-a-take.md`
  (exemplo: `trabalhos/verdades-shape-slim/`).

No começo de um vídeo novo, perguntar qual formato usar.

## Como trabalhar com o usuário (regras combinadas)

- Falar em português, em linguagem simples, explicando o que está sendo feito.
- Ir **por etapas**: mostrar o resultado no fim de cada uma e **esperar o ok** antes de seguir.
- **Perguntar antes** de instalar programas, usar APIs pagas ou apagar arquivos.
- Nunca mostrar chaves de API na tela nem salvá-las em arquivos do projeto.
- Revisar sozinho (folha de contato + `--revisar`) **antes** de mostrar prévias.
- Renderizar o vídeo completo **só depois do ok** do usuário.

## Fluxo para um vídeo novo

1. O usuário coloca o arquivo bruto em `Bruto/` (de preferência **sem legenda gravada**).
2. Perguntar rapidamente: o assunto e a frase-gancho, se quer contador por capítulo
   (ex.: `"verdade #{n}"`), se quer chamada final para seguir e quais palavras difíceis existem.
3. Transcrever:
   `.venv\Scripts\python fazer_video.py Bruto\ARQUIVO --nome NOME --dica "..." --so-previa --sem-pausas`
   (ou passo a passo, sem `--sem-pausas`).
4. Mostrar o texto (`trabalhos/NOME/revisao.txt`), sugerir correções e aplicá-las com o ok do usuário
   (editar `revisao.txt` e depois rodar `transcrever.py ARQUIVO --nome NOME --aplicar`).
5. **Roteiro de cenas** (a parte criativa): o rascunho automático é só um ponto de partida.
   Reescrever o `trabalhos/NOME/roteiro.json` à mão, no nível do roteiro do primeiro vídeo:
   - cenas de 2 a 4 s, uma ideia por cena, capítulos com transição de rabisco;
   - cada desenho entra na palavra exata; uma palavra-chave por cena com `"impacto": true`;
   - preferir **metáforas visuais** (objetos) a escrever a frase; texto só em rótulos curtos;
   - **não desenhar corpos ou silhuetas** (tema sensível de pressão estética): usar objetos;
   - piadas visuais recorrentes funcionam bem (ex.: objetos com medo, pão francês de boina);
   - usar as cenas modelo quando couber (lista, comparação, número grande, antes e depois,
     passo a passo, chamada para seguir).
   Validar com `ver_roteiro.py NOME` e mostrar a tabela (`roteiro.md`) para aprovação.
6. Revisão automática + prévia:
   `renderizar.py NOME --revisar` (com `--pixels` se houver legenda antiga) e
   `renderizar.py NOME --previa` (e `--guias` para conferir rosto e áreas seguras).
   Corrigir até zerar e mostrar a folha de contato + 1 ou 2 trechos (`--trecho a-b`).
7. Com o ok: `renderizar.py NOME` gera o vídeo final e a versão para celular em `trabalhos/NOME/saida/`.

## Identidade visual (não mudar sem o usuário pedir)

Direção **"Correção a Caneta"**, paleta **Ameixa**: tinta ameixa `#6E2A6B`, marca-texto pêssego `#FFB48F`,
papel `#FFF8F1`, texto `#2A1A2B`, apoio rosa `#D9467A`. Fontes Permanent Marker (anotações) e Shantell Sans
(legenda). Traço à mão "fervendo" a 12 fps, entradas com passada, impacto com zoom + tremida + boing.
Tudo isso vem do `estilo.json`: nada de cor, fonte ou tempo fixo no código.
Proibido: neon, glitch, brilhos e partículas de IA, gradiente 3D, colagem com etiquetas datilografadas e carimbos.

## Mapa do código

- `fazer_video.py`: comando único (transcrição → rascunho → revisão → render).
- `motor/`:
  - `transcricao.py`, `audio.py`: transcrição e áudio;
  - `rascunho.py`: roteiro automático;
  - `modelos.py`: cenas modelo;
  - `roteiro.py`: validador;
  - `biblioteca.py`: os desenhos;
  - `desenho.py`: traço à mão;
  - `cenas.py`: animações e layout que desvia do rosto;
  - `legenda.py`, `transicoes.py`, `som.py`, `render.py`, `revisao.py`, `rosto.py`, `estilo.py`.
- `montar_biblioteca.py`: catálogo dos desenhos (`biblioteca/catalogo.png`).
- `ferramentas/demo_modelos.py`: demonstração das 6 cenas modelo.
- `ferramentas/revisar.html`: revisão do texto palavra por palavra. Abrir pelo preview "previa"
  do `.claude/launch.json`, em `/ferramentas/revisar.html?video=/Bruto/ARQ&palavras=/trabalhos/NOME/palavras.json`.

## Armadilhas já conhecidas

- Sempre usar `.venv\Scripts\python` (o `python` do Windows é só um atalho da Loja).
- O caminho do usuário tem "ç" (`Gonçalves`): o OpenCV não abre arquivos por caminho. Carregar pela memória (já feito em `rosto.py`).
- faster-whisper 1.2.1 + PyAV 19 quebram a leitura de arquivo: decodificar com ffmpeg e passar numpy (já feito).
- O OpenCV 5 não tem mais Haar cascade: o rosto usa YuNet (`modelos/face_detection_yunet_2023mar.onnx`).
- Redimensionar desenhos com BOX/BILINEAR (LANCZOS/BICUBIC criam um brilho branco junto das linhas).
- Placa de vídeo: RTX 2060 6 GB. O render leva ~4 min por minuto de vídeo.
