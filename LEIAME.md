# Reels animados por código

Transforma um vídeo (ou só um áudio) de alguém falando num **Reel vertical 1080x1920** com desenhos animados no estilo *Correção a Caneta · Ameixa*, legenda palavra por palavra, transições e efeitos sonoros — tudo gerado por código, sem editor de vídeo.

---

## Uso rápido

Coloque o arquivo na pasta `Bruto\` e rode, dentro da pasta do projeto:

```
.venv\Scripts\python fazer_video.py Bruto\meu_video.mp4
```

Aceita **vídeo** (mp4, mov…) ou **só áudio** (m4a, mp3, wav). Vídeo horizontal também funciona: ele é ampliado e cortado no centro. Áudio puro vira uma folha de caderno com os desenhos no meio.

O comando faz 5 etapas e **para entre elas** para você revisar (Enter continua, Ctrl+C para):

| Etapa | O que acontece | Você revisa |
|---|---|---|
| 1. Transcrição | Transcreve com o tempo de cada palavra (GPU, ~20 s) | `revisao.txt`: corrija palavras erradas |
| 2. Roteiro | Monta um **rascunho** de cenas, desenhos e modelos | `roteiro.md` (tabela) e, se quiser mudar, `roteiro.json` |
| 3. Revisão + prévia | Confere as regras sozinho e gera a folha de contato | `previa.png` e a lista de pontos a olhar |
| 4. Render | Vídeo completo 1080x1920 (~4 min para 1 min de vídeo) | — |
| 5. Versão leve | Cópia 720x1280 para mandar pelo celular | — |

Se você parar no meio, rode **o mesmo comando** de novo: ele reaproveita a transcrição e o roteiro que já existem (com as suas correções).

### Opções

| Opção | Para quê |
|---|---|
| `--nome NOME` | Nome da pasta do trabalho (padrão: nome do arquivo) |
| `--contador "verdade #{n}"` | Escreve um contador no canto a cada capítulo (`{n}` vira 1, 2, 3…) |
| `--chamada "me segue pra mais!"` | Cena final "chamada para seguir", com seta apontando para o perfil |
| `--dica "carboidrato, CLT, whey"` | Palavras difíceis do assunto, para a transcrição acertar |
| `--cobrir-legenda` | O vídeo **já tem legenda gravada**: a nossa fica sempre por cima dela |
| `--refazer-roteiro` | Gera um novo rascunho do roteiro (mantém a transcrição corrigida) |
| `--refazer` | Transcreve e monta tudo de novo (perde as revisões) |
| `--so-previa` | Para depois da folha de contato, sem renderizar |
| `--sem-pausas` | Não espera Enter entre as etapas |

Exemplo completo:

```
.venv\Scripts\python fazer_video.py Bruto\verdades.mp4 --contador "verdade #{n}" --chamada "me segue pra mais verdades!" --dica "carboidrato, CLT, proteína"
```

---

## Onde ficam as coisas

```
Videos\
├─ fazer_video.py          o comando único
├─ estilo.json             TODA a identidade visual: cores, fontes, traço, tempos, sons, zonas
├─ Bruto\                  seus vídeos/áudios originais
├─ trabalhos\<nome>\       um trabalho por vídeo
│   ├─ revisao.txt         texto para você corrigir
│   ├─ palavras.json       transcrição corrigida (tempo de cada palavra)
│   ├─ palavras_original.json   transcrição crua (as correções são aplicadas em cima dela)
│   ├─ roteiro.json        o roteiro que o motor lê
│   ├─ roteiro.md          o mesmo roteiro em tabela, para ler
│   ├─ rosto.json          onde o rosto está a cada instante (calculado uma vez)
│   ├─ previa.png          folha de contato
│   └─ saida\              <nome>_1080x1920.mp4 e <nome>_celular.mp4
├─ motor\                  o código (tempo, desenho, cenas, legenda, transições, som, render…)
├─ biblioteca\             catálogo dos desenhos, demo dos modelos
├─ fontes\                 Permanent Marker e Shantell Sans (licenças livres)
└─ modelos\                modelos de transcrição e de rosto (baixados uma vez)
```

---

## Revisar o texto (`revisao.txt`)

Uma frase por linha, com o tempo em que ela começa:

```
[00:12.9] A internet convenceu vocês que ser magra é o que importa e ter saúde é meio relevante.
```

Corrija direto na linha (pode trocar, juntar ou separar palavras) e salve. **Não apague nem crie linhas** com `[tempo]`. O tempo de cada palavra é recalculado sozinho. As palavras de baixa confiança aparecem no topo do arquivo.

Para ouvir e conferir palavra por palavra, abra `ferramentas\revisar.html` num servidor local (veja *Ferramentas extras*).

---

## Revisar o roteiro

O rascunho automático é um **ponto de partida**: ele corta a fala em cenas de 2–4 s, escolhe a palavra-chave de cada cena, procura um desenho que combine (pão para "carboidrato", halter para "treino"…) e reconhece padrões que viram **cenas modelo** (número grande, lista, passo a passo). Leia `roteiro.md` e ajuste o `roteiro.json` à vontade.

### Formato do `roteiro.json`

```json
{
 "fonte": "Bruto/meu_video.mp4", "inicio": 0.0, "fim": 58.0,
 "opcoes": { "cobrir_legenda_antiga": false },
 "capitulos": [ { "n": 1, "nome": "verdade #1", "palavra_inicio": 12 } ],
 "cenas": [ { "id": "C02", "palavras": [12, 17], "chave": 17, "metafora": "..." } ],
 "elementos": [
  { "id": "pao", "desenho": "pao", "zona": "lado_direito",
    "entra": { "em": 63, "palavra": "medo", "anim": "pop" },
    "acoes": [ { "em": 65, "palavra": "carboidrato", "anim": "circular", "impacto": true },
               { "em": 72, "palavra": "francês", "anim": "boina" } ],
    "sai":   { "em": 73, "palavra": "As", "anim": "borracha" } }
 ]
}
```

- **`em`** é o número da palavra em `palavras.json` (contando do zero). **`palavra`** é só para conferência: se não bater, o validador avisa.
- **`atraso`** (opcional, em segundos) atrasa o gatilho em relação à palavra.
- Cada cena precisa de **exatamente um** gatilho com `"impacto": true`, na palavra `chave` (zoom com mola + tremida + som).
- Sem `sai`, o desenho fica até a próxima transição de capítulo.
- Outros campos do elemento viram parâmetros do desenho: `texto`, `tamanho`, `escala`, `slot` (`[i, n]` divide a zona em n partes), `tremendo`.
- **Capítulos**: entre um e outro entra a transição de rabisco.

### Zonas (onde o desenho fica)

`topo_esquerdo` (contador), `topo_centro`, `topo_direito`, `lado_esquerdo`, `lado_direito`, `peito_esquerdo`, `peito_direito`, `abaixo_legenda`, `palco` (o meio inteiro — para áudio puro), `perto_da_cabeca` (ao lado da cabeça, acompanhando).

Pendurado em outro desenho: `acima:<id>`, `abaixo:<id>`, `direita:<id>`, `esquerda:<id>`, `dentro:<id>`.
Seta entre dois desenhos: `"zona": "de:<id>>para:<id>"` (ou `para:@x,y` para um ponto da tela).

O motor **sempre afasta os desenhos do rosto**, do contador e uns dos outros, quadro a quadro. A zona é só a preferência.

### Desenhos da biblioteca

balanca, balao_fala, balao_pensamento, biceps, binoculos, borrifador, cartao_papel, casa, celular, check, cifroes, circulo, contador, coracao, coracoes, cracha, cronometro, dinheiro, espelho, etiqueta_preco, fabrica, fita_metrica, garrafa_agua, gotas_suor, grafico, guarda_sol, halter, item_lista, lampada, lista_tarefas, lupa, megafone, ondas, pao, prato_salada, relogio_ponto, ring_light, sacola, selo, seta_subindo, sol, tapete_yoga, tenis, texto_mao, transferidor, wifi, xis

Veja todos em `biblioteca\catalogo.png`. Para criar um novo, siga os exemplos em `motor\biblioteca.py`.

### Animações

- **Entrada:** `pop`, `colar`, `cair`, `fincar`, `desenhar`, `escrever`, `escrever_e_circular`, `subir`, `borrifar`, `procurar`, `desenrolar`, `balancar`, `balancar_e_circular`, `acender`, `contar_numero`
- **Ações:** `circular`, `riscar`, `tremer`, `crescer`, `bater`, `apertar`, `pulsar`, `marcar`, `brilhar`, `flexionar`, `levantar`, `espiral`, `gritar`, `tombar`, `voar_longe`, `despencar`, `malabarismo`, `quase_cair`, `procurar`, `contar`, `pingar`, `multiplicar`, `espremer_reflexo`, `suar_mais`, `virar_pao_frances`, `boina`, `desenrolar_longo`, `medir_angulo`, `fumegar`, `marcar_concluido`, `receber_selo`, `voar_e_colar:<id>`
- **Saída:** `borracha` (apaga como se desenhasse ao contrário), `puf`

---

## Cenas modelo

Uma cena pode usar um modelo pronto em vez de elementos soltos: coloque `"modelo"` dentro da cena. Exemplo de cada um (veja todos funcionando em `biblioteca\modelos_demo.png`):

```json
{ "tipo": "lista", "zona": "lado_direito",
  "itens": [ {"em": 10, "texto": "água", "marcar_em": 14}, {"em": 12, "texto": "sono"}, {"em": 14, "texto": "proteína"} ] }

{ "tipo": "passo_a_passo", "passos": [ {"em": 30, "texto": "planeje"}, {"em": 33, "texto": "coma"}, {"em": 36, "texto": "descanse"} ] }

{ "tipo": "numero_grande", "em": 41, "numero": "80", "rotulo": "% é hábito", "zona": "topo_direito" }

{ "tipo": "comparacao", "esquerda": {"em": 50, "texto": "dieta da moda"}, "direita": {"em": 54, "desenho": "prato_salada"},
  "veredito": {"em": 58, "vencedor": "direita"} }

{ "tipo": "antes_depois", "antes": {"em": 62, "desenho": "gotas_suor"}, "depois": {"em": 65, "desenho": "balanca", "texto": ""} }

{ "tipo": "chamada_para_seguir", "em": 80, "texto": "me segue pra mais verdades!" }
```

- `zona` é opcional. Sem ela, comparação e antes e depois usam as laterais do rosto. Com `"zona": "palco"`, usam as duas metades do palco, o melhor para áudio puro.
- `sai_em` (opcional) apaga todos os desenhos do modelo naquela palavra.
- O impacto do modelo cai sozinho no lugar certo: no último item, no veredito, no "depois" ou no número.

---

## Regras que o próprio projeto confere

**No roteiro (`ver_roteiro.py`):** cenas de 2–4 s, uma palavra-chave com impacto por cena, cada gatilho na palavra certa, tela nunca parada por mais de 1 s.

**No vídeo (`renderizar.py --revisar`), quadro a quadro:**
- nada cortado nas bordas;
- legenda nunca coberta;
- áreas do Reels livres (250 px no topo, 380 px na base, coluna de botões à direita);
- rosto livre e desenhos sem sobreposição acidental;
- letra legível no celular (≥ 36 px nos desenhos, ≥ 56 px na legenda).

Com `--pixels`, também confere se alguma legenda ou título antigo gravado no vídeo vaza.

---

## Ferramentas extras

| Comando | Para quê |
|---|---|
| `.venv\Scripts\python renderizar.py <nome> --previa` | Folha de contato (1 quadro por cena) |
| `... renderizar.py <nome> --previa --guias` | Idem, com áreas do Reels (vermelho) e cabeça (azul) marcadas |
| `... renderizar.py <nome> --previa --tempos 3.5,17.6` | Só esses instantes |
| `... renderizar.py <nome> --trecho 12-19` | Vídeo leve só de um trecho (para conferir movimento e som) |
| `... renderizar.py <nome> --revisar --pixels` | Revisão automática completa |
| `... renderizar.py <nome>` | Render completo + versão para celular |
| `... ver_roteiro.py <nome>` | Valida o roteiro e regera `roteiro.md` |
| `... transcrever.py <arquivo> --nome <nome> --aplicar` | Reaplica as correções do `revisao.txt` |
| `... montar_biblioteca.py` | Redesenha o catálogo (depois de mudar o estilo ou criar desenho) |
| `... ferramentas\demo_modelos.py` | Gera a demonstração das 6 cenas modelo |
| `... testar_ambiente.py` | Confere se Python, ffmpeg, fontes e GPU estão funcionando |

A página `ferramentas\revisar.html` toca o vídeo com o texto acendendo palavra por palavra. Ela precisa de um servidor local: no Claude Code, peça "abre a revisão do trabalho X".

---

## Mudar o estilo

Tudo vem do `estilo.json`; não há cor, fonte ou tempo fixo no código.

- **`cores`**: papel, tinta, marca-texto, texto, apoio.
- **`fontes`**: arquivos em `fontes\`.
- **`traco`**: espessura, tremor, a "fervura" da linha.
- **`movimento`**: curvas e durações.
- **`transicao`**: o rabisco entre capítulos.
- **`legenda`**: posição, tamanho, palavra-chave.
- **`sons`**: volume, parâmetros de cada efeito e qual animação toca qual som.
- **`zonas`**: onde os desenhos ficam.
- **`saida`**: qualidade do vídeo e -14 LUFS.

Depois de mudar, rode `montar_biblioteca.py` para ver o catálogo novo.

---

## Problemas comuns

- **"Python não encontrado"**: use sempre `.venv\Scripts\python`, não só `python`.
- **Transcrição lenta**: sem placa NVIDIA, ela roda na CPU com o modelo `small` automaticamente.
- **Palavra errada recorrente**: passe `--dica "palavra1, palavra2"`.
- **Desenho em cima do rosto num instante**: rode `renderizar.py <nome> --previa --guias --tempos <instante>` para ver; troque a zona ou o tamanho (`escala`) no `roteiro.json`.
- **Vídeo com legenda gravada**: use `--cobrir-legenda`. A faixa da nossa legenda fica fixa sobre a área onde Reels costumam ter legenda (meio-baixo da tela). Confira com `--revisar --pixels`.
- **Para reinstalar tudo igual**: `.venv\Scripts\python -m pip install -r requirements-travado.txt`.

**Fontes:** Permanent Marker (Apache 2.0) e Shantell Sans (OFL). As licenças estão em `fontes\`.
