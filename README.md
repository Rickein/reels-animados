# Reels animados por código

Transforma um vídeo de rosto falando (ou só um áudio) num **Reel vertical 1080x1920**. O resultado tem
desenhos à mão animados, legenda palavra por palavra, transições e efeitos sonoros, tudo gerado por
código (Python + Pillow + ffmpeg + faster-whisper), sem editor de vídeo.

Funciona junto com o **Claude Code**: a skill `reels-animados` (em `.claude/skills/`) guarda a metodologia,
as regras combinadas e os formatos prontos.

## Num computador novo (Windows)

1. Instale o [Git](https://git-scm.com/download/win) e o [Claude Code](https://claude.com/claude-code).
2. Baixe o projeto:
   ```
   git clone https://github.com/SEU-USUARIO/reels-animados.git
   ```
3. Abra a pasta no Claude Code e peça: **"instala o projeto"**. A skill explica o que vai instalar e pede
   o ok antes. Também dá para rodar direto:
   ```
   powershell -ExecutionPolicy Bypass -File instalar.ps1
   .venv\Scripts\python testar_ambiente.py
   ```

## Fazer um vídeo

Coloque o arquivo em `Bruto/` e diga ao Claude: **"coloquei um vídeo novo no Bruto, vamos fazer um reel"**.
A partir daí, ele conduz as etapas:

1. formato;
2. transcrição;
3. roteiro de cenas;
4. prévia;
5. render.

Ele para em cada uma e espera o seu ok antes de seguir.

- `formatos/`: os estilos de vídeo já criados (Correção a Caneta, Take a Take) e roteiros de exemplo.
- `LEIAME.md`: o manual técnico completo.
- `estilo.json`: toda a identidade visual (cores, fontes, tempos, sons, zonas).

Os vídeos brutos, os trabalhos e os modelos baixados **não** vão para o GitHub (veja `.gitignore`).

**Fontes:** Permanent Marker (Apache 2.0), Shantell Sans (OFL) e Montserrat (OFL). As licenças estão em `fontes/`.
