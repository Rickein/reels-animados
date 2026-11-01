---
name: reels-animados
description: Transforma um vídeo de rosto falando (ou só um áudio) da pasta Bruto/ num Reel vertical 1080x1920 com desenhos à mão animados, legenda palavra por palavra, números, transições e sons, tudo por código (Python + Pillow + ffmpeg + faster-whisper). Use quando o usuário pedir para fazer um reel, um vídeo novo, disser que colocou um arquivo no Bruto, ou pedir para ajustar, revisar ou renderizar um trabalho em trabalhos/. Também cobre a instalação da ferramenta num computador novo.
---

# Reels animados por código

Você cuida da direção de motion design e da programação desta ferramenta. O usuário grava o vídeo e você
transforma em Reel, **por etapas e sempre com o ok do usuário**.

O manual técnico completo (comandos, formato do `roteiro.json`, zonas, desenhos e animações) está em
`LEIAME.md`, na raiz do projeto. Os formatos de vídeo prontos estão em `formatos/`. Leia os dois quando precisar.

## Regras combinadas (valem sempre)

- Fale em **português**, em linguagem simples, explicando o que está sendo feito.
- Trabalhe **por etapas**: mostre o resultado no fim de cada uma e **espere o ok** antes de seguir.
- **Pergunte antes** de instalar programas, usar APIs pagas ou apagar arquivos.
- Nunca mostre chaves de API na tela nem as salve em arquivos do projeto.
- **Revise por conta própria** (folha de contato + `--revisar`) antes de mostrar qualquer prévia.
- Renderize o vídeo completo **só depois do ok** do usuário.
- Use sempre `.venv\Scripts\python`. O `python` do Windows é só um atalho da Loja.
  Antes dos scripts, defina `PYTHONIOENCODING=utf-8` (no PowerShell: `$env:PYTHONIOENCODING="utf-8"`).

## 0. Computador novo? Instale primeiro

Se não houver a pasta `.venv` ou os modelos, **explique o que será instalado e peça o ok**. A instalação inclui:
- Python 3.12 e ffmpeg (via winget), se ainda não existirem;
- as bibliotecas Python do projeto;
- o modelo de recorte MODNet (~26 MB).

Com o ok, rode:

```
powershell -ExecutionPolicy Bypass -File instalar.ps1
```

Depois rode `.venv\Scripts\python testar_ambiente.py` e mostre o resultado. Os modelos de transcrição
(~1,6 GB) são baixados sozinhos no primeiro uso. Sem placa NVIDIA, tudo funciona na CPU, só que mais devagar.

## 1. Começo de um vídeo novo

O arquivo bruto fica em `Bruto/`, de preferência **sem legenda gravada**. Pergunte, numa mensagem só:

1. **Qual formato?** Leia as receitas em `formatos/`:
   - **Correção a Caneta** (`formatos/correcao-a-caneta.md`): tira de caderno, contador, rabisco entre capítulos, sons em tudo.
   - **Take a Take** (`formatos/take-a-take.md`): lista com um take por item, número subindo por trás da
     cabeça, legenda limpa que fica lilás, som mínimo e desenhos no centro.
2. A frase-gancho e o assunto.
3. Se quer contador por capítulo e se quer chamada final para seguir.
4. As palavras difíceis (marcas, gírias, termos técnicos).
5. Se há algo para **não** comentar ou desenhar em algum trecho.

## 2. Transcrição

```
.venv\Scripts\python fazer_video.py Bruto\ARQUIVO --nome NOME --dica "..." --so-previa --sem-pausas
```

Mostre `trabalhos/NOME/revisao.txt` e sugira correções. Com o ok do usuário, edite `revisao.txt` e rode
`transcrever.py Bruto\ARQUIVO --nome NOME --aplicar`. Se o vídeo tiver vários takes, ache os cortes com
`ffmpeg -i Bruto\ARQ -vf "scdet=threshold=8" -an -f null - 2>&1 | findstr scd.time`.

## 3. Roteiro de cenas (a parte criativa)

O rascunho automático é só um ponto de partida. **Reescreva o `trabalhos/NOME/roteiro.json` à mão**, no nível
dos exemplos em `formatos/exemplos/`:

- cenas de 2 a 4 s, com uma ideia por cena;
- cada desenho entra na palavra exata, e cada cena tem **uma** palavra-chave com `"impacto": true`;
- prefira **metáforas visuais** (objetos) a escrever a frase; use texto só em rótulos curtos;
- **não desenhe corpos nem silhuetas**, porque o tema é sensível (pressão estética). Use objetos. Só abra
  exceção se o usuário pedir. Exemplo: a barriga "seca" com tanquinho do vídeo 2;
- piadas visuais recorrentes funcionam bem: objetos com medo, pão francês de boina, teia de aranha com cara triste no que foi "esquecido";
- use as cenas modelo quando couber: lista, comparação, número grande, antes e depois, passo a passo, chamada para seguir;
- se faltar um desenho, crie-o em `motor/biblioteca.py`, seguindo os existentes, e confira em `montar_biblioteca.py`.

Valide com `ver_roteiro.py NOME` e mostre a tabela (`roteiro.md`) para aprovação.

## 4. Revisão automática + prévia

```
.venv\Scripts\python renderizar.py NOME --revisar            (com --pixels se houver legenda antiga)
.venv\Scripts\python renderizar.py NOME --previa --guias
.venv\Scripts\python renderizar.py NOME --trecho 5-12
```

Corrija até a revisão zerar. Olhe primeiro a folha de contato (`previa.png`) e só depois mostre ao
usuário a folha + 1 ou 2 trechos. Ajuste o que for pedido e repita.

## 5. Render final (só com o ok)

`renderizar.py NOME` gera `trabalhos/NOME/saida/NOME_1080x1920.mp4` e a versão para celular. O render leva
uns 4 min por minuto de vídeo numa RTX 2060.

Se o usuário pedir um estilo novo e gostar do resultado, salve-o como formato novo em
`formatos/NOME-DO-FORMATO.md`, seguindo `formatos/take-a-take.md`, e acrescente o formato à lista do passo 1 desta skill.

## Identidade visual (não mude sem o usuário pedir)

- **Direção:** "Correção a Caneta", paleta **Ameixa**:
  - tinta ameixa `#6E2A6B`;
  - marca-texto pêssego `#FFB48F`;
  - papel `#FFF8F1`;
  - texto `#2A1A2B`;
  - apoio rosa `#D9467A`.
- **Fontes:** Permanent Marker (anotações), Shantell Sans (legenda à mão) e Montserrat SemiBold (legenda simples e números do Take a Take).
- **Animação:** traço à mão "fervendo" a 12 fps, entradas com passada, impacto com zoom + tremida + boing.
- Tudo vem do `estilo.json`. Não coloque cor, fonte ou tempo fixo no código.
- **Proibido:** neon, glitch, brilhos e partículas de IA, gradiente 3D, colagem com etiquetas datilografadas e carimbos.
- O Instagram corta as laterais. Nos formatos novos, mantenha os desenhos no meio da tela (`faixa_central`).

## Armadilhas já conhecidas

- **Caminhos com acento** (ex.: "Gonçalves"): o OpenCV não abre o arquivo pelo caminho. Carregue pela memória (já feito em `rosto.py`).
- **faster-whisper 1.2.1 + PyAV 19** quebram a leitura de arquivo. Decodifique com ffmpeg e passe numpy (já feito).
- **OpenCV 5** não tem Haar cascade. O rosto usa YuNet (`modelos/face_detection_yunet_2023mar.onnx`).
- **Redimensionar desenhos:** use BOX ou BILINEAR. LANCZOS e BICUBIC criam um brilho branco junto das linhas.
- **Recorte da pessoa** (MODNet): roda na CPU, é calculado uma vez e fica guardado em `trabalhos/NOME/recorte.npz`.
- **Revisão de texto palavra por palavra:** use o preview "previa" do `.claude/launch.json`, em
  `/ferramentas/revisar.html?video=/Bruto/ARQ&palavras=/trabalhos/NOME/palavras.json`.
