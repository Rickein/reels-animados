# Formato "Take a Take"

## O que é

Reel em formato de **lista**, gravado com **um take para cada item**. A cada corte de take, um **número
grande sobe por trás da cabeça** de quem fala, aparece por um instante e some devagar. A legenda é
**limpa**: letra de forma, sem caixa e sem contorno, e as palavras ficam lilás conforme são faladas.
Os desenhos à mão aparecem **pequenos e no meio da tela**, acima da cabeça ou no peito. O som é
mínimo: só o número subindo e um "boing" na palavra-chave.

A sensação é mais leve e elegante que a da "Correção a Caneta" do primeiro vídeo. O conteúdo vem na
frente e os desenhos só pontuam.

- **Primeiro vídeo neste formato:** `trabalhos/verdades-shape-slim/`
  ("7 verdades sobre emagrecimento e shape slim", 36 s).
- **Quando usar:** vídeos tipo "X verdades / X erros / X dicas", em que cada item é um take separado.
- **Quando não usar:** vídeo de um take só, sem cortes. Nesse caso não há onde o número subir.
  Prefira o estilo do primeiro vídeo.

## Perguntas rápidas no começo

1. Qual é a frase-gancho? Ela vira o título escrito à mão nos primeiros segundos.
2. Quantos itens são? Cada item é mesmo um take separado? Eu confiro os cortes com `scdet`.
3. Tem alguma cena para **não** comentar ou desenhar? No vídeo 2, por exemplo, nada perto da boca no take do sofá.
4. Tem palavras difíceis, marcas ou gírias? Exemplo: "beber igual um opala".
5. Quer chamada final para seguir? No vídeo 2 não teve.

## Receita: o `"opcoes"` do roteiro.json

```json
"opcoes": {
  "legenda": "simples",
  "transicoes": [1],
  "desvio_estavel": true,
  "faixa_central": [150, 930],
  "desvio_janela": 1.2,
  "aparar_testa": 0.15,
  "sons": { "categorias": ["impacto", "numero", "transicao"], "troca": { "transicao": "pagina_suave" } },
  "numeros_atras": [ { "n": 1, "t": 5.367 }, { "n": 2, "t": 9.633 } ]
}
```

- `legenda: "simples"`: legenda Montserrat SemiBold de 62 px, amarelo claro `#FFF3B0`, palavra falada
  em lilás `#C9A0FF` e sombra suave por trás, em y = 1450. Os valores ficam em `estilo.json` → `legenda.variantes.simples`.
- `numeros_atras`: um item por take, com `t` igual ao segundo exato do corte. Para achar os cortes:
  `ffmpeg -i Bruto/ARQ -vf "scdet=threshold=8" -an -f null - 2>&1 | grep scd.time`.
  O recorte da pessoa (MODNet, `modelos/modnet/modnet.onnx`) é calculado uma vez e guardado em `recorte.npz`.
  A fonte, o tamanho e o tempo de sumir do número ficam em `estilo.json` → `numero_atras`.
- `transicoes: [1]`: o rabisco aparece só do gancho para o item 1. Os outros itens trocam no corte seco do take.
- `sons`: só tocam o boing da palavra-chave (`impacto`), o rangido do número (`numero`) e uma página
  suave na única transição. Não há pop nem caneta quando os desenhos entram.
- `faixa_central`, `desvio_estavel`, `desvio_janela`, `aparar_testa`: deixam os desenhos no meio da tela,
  porque o Instagram corta as laterais. Cada desenho escolhe um lugar e fica nele, sem pular. Os desenhos
  também desviam do número.

## Regras do roteiro de cenas

- Duas cenas por item, em geral "faz X" e depois "mas esquece Y". Cada cena tem uma palavra-chave com `"impacto": true`.
- **Primeiro desenho do item:** zona `centro_baixo`, no peito. O número ainda está no alto nesse momento.
- **Segundo desenho do item:** zona `centro_cima`, acima da cabeça, quando o número já está sumindo.
- No gancho, use `texto_mao` na zona `faixa_peito`: a frase escrita aparece, é apagada e a seguinte entra com círculo.
- **Piada recorrente:** o que foi "esquecido" ganha **teia de aranha e cara triste** (animação `abandonar`).
  Desenhos com esse suporte: `prato`, `halter`, `brocolis`, `balanca_cozinha`, `garrafa_agua`.
- Quando a pessoa se mexe muito no take, tire o desenho antes (`"sai"`), para não encostar no rosto.
- Desenhos criados para o vídeo 2 (em `motor/biblioteca.py`): poltrona, xicara, riscos, prato, calendario,
  balde, pizza, acucar, opala, chope, pote_whey, brocolis, barriga, balanca_cozinha, prancheta, rolinho.
- Animações novas: `abandonar`, `correr`, `rolar`, `esvaziar`, `marcar_dias`, `pintar_fds`, `contar_riscos`, `transbordar`.

## Passo a passo

1. `transcrever.py Bruto\ARQ --nome NOME --dica "..."`, depois revisar o texto com o usuário.
2. Achar os cortes com `scdet` e conferir se batem com o início de cada item.
3. Escrever o `roteiro.json` com as opções acima e validar com `ver_roteiro.py NOME`.
4. Rodar `renderizar.py NOME --revisar` até zerar. Depois gerar a prévia com
   `--previa --tempos ...`, escolhendo instantes fora da transição, e 1 ou 2 trechos com `--trecho a-b`.
5. Renderizar o vídeo final só com o ok do usuário: `renderizar.py NOME`.
