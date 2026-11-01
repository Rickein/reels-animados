# Formato "Correção a Caneta"

## O que é

O formato padrão, do primeiro vídeo. A tela parece uma **página corrigida a caneta**: desenhos à mão
"fervendo" em tinta ameixa, marca-texto pêssego, legenda numa **tira de caderno** em letra à mão
(Shantell Sans), um **contador** no canto ("verdade #n"), **rabisco** entre os capítulos e efeitos
sonoros em quase tudo (pop, caneta, boing). É mais divertido e cheio que o "Take a Take".

- **Primeiro vídeo neste formato:** `trabalhos/verdades-magreza/` ("7 verdades sobre a pira da magreza").
- **Exemplo de roteiro:** `formatos/exemplos/correcao-a-caneta_verdades-magreza.json`.
- **Quando usar:** vídeo de um take só ou com poucos cortes, conteúdo provocativo e engraçado.

## Receita

- É o padrão do motor: não precisa de `"opcoes"` especiais.
- `fazer_video.py ... --contador "verdade #{n}"` liga o contador por capítulo.
- `--chamada "me segue pra mais!"` adiciona a cena final para seguir.
- `--cobrir-legenda`: use quando o bruto já tiver **legenda gravada**. A nossa fica por cima.
  No roteiro, isso vira `"cobrir_legenda_antiga": true`. Se também houver um título antigo, use
  `"cobrir_titulo_antigo_ate": SEGUNDOS`. Confira com `renderizar.py NOME --revisar --pixels`.

## Regras das cenas

- Desenhos nas laterais do rosto (`lado_esquerdo`, `lado_direito`, `peito_*`) e o contador em `topo_esquerdo`.
- Piadas recorrentes: objetos com medo e o pão francês de boina.
- Use as cenas modelo quando couberem: lista, comparação, número grande, antes e depois, passo a passo e chamada para seguir.
