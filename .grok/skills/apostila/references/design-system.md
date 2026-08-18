# Design system da apostila

O CSS vive em `assets/apostila.css` e é embutido no HTML por `montar.py`. Você escreve apenas
`corpo.html` — o fragmento com as seções — usando as classes abaixo. Não escreva `<style>`,
não use atributo `style=`, não invente classe: o que não está aqui não tem estilo.

## Paleta e por que ela é assim

| token | cor | uso |
|---|---|---|
| azul-tinta | `#0B3C5D` | títulos, numeração de seção, faixa |
| azul | `#14639E` | filetes, marcadores, links |
| azul-tint | `#E9F2F8` | fundo de caixa (6% de tinta) |
| verde-fundo | `#0E6B4F` | subtítulos, checkpoints |
| verde | `#12805C` | realce de termo, mnemônico |
| âmbar | `#9A5B00` | **exclusivo** de "pegadinha de prova" |

Azul organiza (estrutura, hierarquia), verde sinaliza o que fixar, âmbar interrompe. Um alerta
que aparece toda hora deixa de ser alerta — por isso âmbar tem dono único.

Impressão em preto e branco continua legível: cada elemento se distingue por filete, peso e
posição, nunca só por cor.

## Estrutura do corpo

```html
<h2 id="s1">Título da primeira seção</h2>
<p>Texto…</p>
<h3>Subtítulo</h3>
<p>Texto…</p>
<div class="checkpoint">…</div>

<h2 id="s2">Título da segunda seção</h2>
…

<div class="quadro-sintese">
  <h2 class="sem-numero">Síntese da aula</h2>
  <ul><li>…</li></ul>
</div>
```

- `<h2>` numera automaticamente e entra no mapa da aula. Use `class="sem-numero"` para o que
  não é seção de conteúdo (a síntese final).
- `id` em cada `<h2>` é opcional, mas ajuda a referenciar seções nas questões.
- Nada de `<h1>`: o título da aula vem do `meta.json`.

## Caixas de sinalização

Todas seguem `<aside class="box TIPO"><h4>Rótulo</h4>…</aside>`. **Uma a cada ~250 palavras.**

```html
<div class="box chave">
  <h4>Ponto-chave</h4>
  <p>A separação de Poderes é <strong>cláusula pétrea</strong> (art. 60, § 4º, III).</p>
</div>

<div class="box pegadinha">
  <h4>Pegadinha de prova</h4>
  <p>Bancas trocam <b>livre iniciativa</b> por <b>livre concorrência</b>.</p>
</div>

<div class="box lei">
  <h4>Lei seca</h4>
  <p>Art. 1º A República Federativa do Brasil […] tem como fundamentos: I — a soberania; …</p>
</div>

<div class="box mnemonico">
  <h4>Mnemônico</h4>
  <p><strong>SO-CI-DI-VA-PLU</strong> — <b>So</b>berania, <b>Ci</b>dadania, …</p>
</div>
```

| tipo | para quê | não use para |
|---|---|---|
| `chave` | a ideia que sustenta a seção | repetir o parágrafo anterior |
| `pegadinha` | o erro concreto que a banca explora | qualquer observação genérica |
| `lei` | transcrição literal do dispositivo | paráfrase sua |
| `mnemônico` | truque de memorização de rol | frase de efeito |

## Blocos didáticos

Diferentes das caixas: fazem parte do fluxo do texto, vêm sem fundo colorido e **não entram no
limite de densidade**. Use à vontade — são eles que transformam enunciado em ensino. O rótulo é
gerado pelo CSS; não escreva título dentro deles.

```html
<div class="exemplo">
  <p>Uma associação expulsou um sócio sem deixá-lo se defender. O STF anulou a expulsão,
  mesmo tratando-se de entidade privada (RE 201.819/RJ).</p>
</div>

<div class="em-outras-palavras">
  <p>Direito fundamental não vale só contra o Estado: vale também entre particulares.</p>
</div>

<ol class="passo-a-passo">
  <li>Identifique quem editou o ato: se foi o Executivo, comece pelo art. 49, V.</li>
  <li>Verifique se o ato exorbitou do poder regulamentar.</li>
  <li>Se exorbitou, o Congresso pode sustá-lo — é freio, não invasão de competência.</li>
</ol>
```

| bloco | quando usar |
|---|---|
| `.exemplo` | caso concreto que ancora um conceito abstrato — **pelo menos um por seção** |
| `.em-outras-palavras` | reformulação simples logo após texto de lei ou definição densa |
| `.passo-a-passo` | raciocínio de duas ou mais etapas, para não pular degrau |

Exemplo bom tem gente, número e situação. "Por exemplo, quando ocorre a hipótese legal" não é
exemplo — é a mesma abstração com outro nome.

## Recuperação ativa

```html
<div class="pare-responda">
  <h4>Pare e responda</h4>
  <p>Sem olhar acima: quais são os cinco fundamentos, na ordem dos incisos?</p>
  <div class="linhas"></div>
</div>
```

`<div class="linhas">` imprime pauta para a resposta à mão. Uma ou duas por aula, no meio do
conteúdo — depois de apresentar algo, antes de seguir adiante.

```html
<div class="checkpoint">
  <h4>Checkpoint da seção</h4>
  <ul>
    <li>Sei recitar os cinco fundamentos na ordem correta.</li>
    <li>Distingo fundamento de objetivo sem hesitar.</li>
  </ul>
</div>
```

Um checkpoint ao final de cada seção, com **duas** afirmações auto-verificáveis (o estudante
marca a caixinha). Escreva no indicativo — "sei…", "distingo…" —, nunca como pergunta.

## Tabelas

```html
<table class="tabela-sintese">
  <caption>Fundamentos × Objetivos: o que cada rol responde</caption>
  <thead>
    <tr><th>Critério</th><th>Art. 1º</th><th>Art. 3º</th></tr>
  </thead>
  <tbody>
    <tr><th scope="row">Pergunta</th><td>Sobre o que se apoia?</td><td>Aonde quer chegar?</td></tr>
  </tbody>
</table>
```

Tabela é o melhor recurso para comparação e o pior para lista. Se só há uma coluna de dados,
use uma lista.

## Fechamento do conteúdo

```html
<div class="quadro-sintese">
  <h2 class="sem-numero">Síntese da aula</h2>
  <ul>
    <li><strong>Art. 1º</strong> — cinco fundamentos e a soberania popular.</li>
  </ul>
</div>
```

Uma linha por seção da aula. `montar.py` acrescenta sozinho, depois disso, a faixa de revisão
espaçada (D+1 / D+7 / D+30), as fontes consultadas e o rodapé — não escreva esses blocos.

## Texto corrido

- `<mark class="termo">termo</mark>` — realce do conceito na primeira vez que aparece.
  No máximo 2 ou 3 por seção; realce demais é o mesmo que nenhum.
- `<strong>` sai em azul: use para o que a prova cobra.
- `<b>` é ênfase neutra dentro de caixas.
- Parágrafos de 3 a 6 linhas. Bloco maior que isso, na coluna de leitura (~152 mm), vira parede.
- Listas com no máximo 7 itens; acima disso, tabela ou divisão em duas.

## Margem de anotação

Desligada por padrão. As margens laterais da folha são iguais (12 mm). Não há filete
de anotação à direita.

## O que nunca fazer

- Emoji no documento. Os ícones vêm do CSS e imprimem nítidos; emoji depende de fonte instalada.
- `style=`, `<font>`, `<center>`, tabela de layout.
- Imagem externa: o HTML precisa continuar funcionando offline, em qualquer máquina.
- Fundo escuro ou texto branco sobre cor — gasta toner e piora a legibilidade.
- Escrever o cabeçalho, o mapa da aula, as questões ou os flashcards no `corpo.html`:
  tudo isso é gerado.
