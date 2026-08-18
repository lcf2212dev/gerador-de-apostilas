---
name: montar-sumario
description: >-
  Monta o sumário de estudo completo de um assunto a partir de um grafo de conteúdo ponderado
  (`grafos/<slug>/grafo.md`, da skill `mapear-conteudo`): dá a cada tópico uma nota de
  importância de 1 a 10, agrupa em módulos, calcula a ordem de estudo respeitando
  pré-requisitos e mostra quanto da prova cada trecho da fila já cobre. Escreve
  `sumarios/<slug>/` com `sumario.md`, `plano.json`, `grade.json` e `lacunas.md`. Use quando o
  usuário disser "monta o sumário de X", "plano de estudos de X", "por onde eu começo", "em que
  ordem estudar X", "o que priorizar nesse edital", "quantas aulas isso vira", ou apontar um
  arquivo de grafo pedindo o roteiro de estudo. A skill `apostila` consome o `plano.json` que
  esta produz. NÃO varre a internet nem calcula incidência (isso é `mapear-conteudo`), NÃO
  escreve aula nem questões (isso é `apostila`) e NÃO monta cronograma com datas.
---

# Montar sumário

Transforma um grafo de incidência em um roteiro de estudo: o que estudar, em que ordem, com que
peso, e quanto da prova aquilo cobre.

O grafo já sabe **o quanto cada tópico cai**. O que ele não sabe é **em que ordem estudar** — e
essa é a pergunta que o concurseiro realmente faz. As duas respostas divergem mais do que parece:
um tópico que cai pouco pode ser a porta de entrada de três que caem muito, e um tópico caríssimo
de 8 horas pode valer menos que quatro tópicos de 1 hora somados. Esta skill resolve essa
diferença com dois números que o grafo não tem: a **centralidade** (quanto o tópico destrava) e a
**importância de 1 a 10** (o valor do tópico medido contra o topo do recorte).

**Divisão de trabalho, herdada de `mapear-conteudo`: o script calcula, o modelo redige.** Nenhum
número do sumário sai de julgamento — todos vêm do `plano.json`, e `conferir` reprova qualquer
percentual ou nota que apareça no markdown sem existir no plano.

---

## O procedimento

### 1. Achar o grafo

```bash
ls grafos/*/grafo.md
```

Sem grafo do assunto, **pare e ofereça `mapear-conteudo`** — ela é que varre editais e provas.
Não monte sumário de memória: o valor inteiro desta skill está em priorizar por incidência
medida, e um sumário sem grafo é um palpite com aparência de plano.

O alvo pode ser o diretório (`grafos/<slug>`, leitura rica via `evidencias.json`), o
`grafo.md` renderizado, ou um `.md` escrito à mão com mermaid ou lista aninhada.

### 2. Ver o que o grafo tem antes de gastar trabalho

```bash
python3 .claude/skills/montar-sumario/scripts/sumario.py inspecionar grafos/<slug>
```

Mostra a cobertura de cada campo. Se `custo_h` estiver em 0%, todas as durações serão estimadas;
se não houver aresta `prerequisito`, não há ordem topológica nem centralidade — e o sumário vira
uma lista ordenada por incidência. Nos dois casos, **diga isso ao usuário antes de prosseguir**,
não depois.

### 3. Priorizar

```bash
python3 .claude/skills/montar-sumario/scripts/sumario.py priorizar grafos/<slug> \
        --assunto "Direito Constitucional" \
        --saida sumarios/<slug>/plano.json
```

O `<slug>` de saída é o do grafo quando o assunto é o escopo inteiro; para um recorte, some o
assunto (`trf-analista-direito-constitucional`). Parâmetros que valem ajustar, e só com motivo
declarado no sumário: `--minutos-aula` (padrão 30; a produção mira o alvo ±5 min), `--beta`
(peso da centralidade, padrão 0.35; `0` desliga), `--sem-prerequisitos` (não puxa pré-requisito
de fora do assunto) e `--sem-lastro` (desliga a regra de lastro — ver a regra 9).

A regra de lastro classifica cada item em `formato` `cheia`, `curta` ou `opcional`, com três
padrões novos: `min_questoes_cheia: 4`, `share_min_cheia: 0.02` e `minutos_max_curta: 30`. Sem
amostra de questões no grafo, ela desliga sozinha com aviso grave.

A matemática inteira — sinais, fórmulas, a escada 1–10 e a calibração — está em
`referencias/priorizacao.md`. Leia antes de explicar qualquer nota ao usuário.

### 4. Escrever o `sumario.md`

Forma exata, seção a seção, em `referencias/anatomia-do-sumario.md`. O trabalho do modelo aqui é
**nomear e agrupar**, não recalcular: dar título legível a cada módulo, decidir onde um tópico de
6 aulas merece ser dividido por assunto e não por relógio, e escrever a frase que explica por que
o primeiro item da fila é o primeiro.

### 5. Escrever a `grade.json`

Uma linha por aula, com o título e o objetivo que a skill `apostila` vai usar. É aqui que o
sumário vira produção. Schema em `referencias/anatomia-do-sumario.md`. A grade não cria aula
para item `opcional`: copie-o para `omitidos` com o motivo do plano (`motivo_omissao`).

### 6. Conferir — laço até aprovar

```bash
python3 .claude/skills/montar-sumario/scripts/sumario.py conferir --plano sumarios/<slug>/plano.json \
        --grade sumarios/<slug>/grade.json --sumario sumarios/<slug>/sumario.md
```

Reprova (exit 2) item esquecido, minutos que não somam, ordem que viola pré-requisito,
importância divergente e — o mais importante — **número no markdown que não existe no plano**.
Corrija e rode de novo. Não entregue nada reprovado.

Item que você decidiu não transformar em aula vai em `omitidos` na grade, com motivo. Omissão
declarada passa; omissão silenciosa reprova.

### 7. Escrever o `lacunas.md`

O bloco `lacunas` do plano, em português: sinais desligados, itens sem incidência, custos
estimados, confiança frágil, ciclos, pré-requisitos importados e a fatia de questões que o
recorte não cobre. Herde também as lacunas do próprio grafo (`lacunas.do_grafo`).

Este arquivo é o que impede o sumário de mentir por omissão. Ele não é rodapé: é o que separa um
plano honesto de um plano confiante.

### 8. Entregar

Os quatro caminhos, a importância média, quantos itens cobrem 50% e 70% da prova, o total de
horas e aulas, e as duas ou três lacunas que mais afetam a confiança. Depois disso, a próxima
skill é `apostila` — e ela lê o `plano.json` sozinha:

```bash
python3 .claude/skills/apostila/scripts/contexto_aula.py sumarios/<slug>/plano.json --seq 1
```

---

## As regras inegociáveis

1. **Nenhum número sai do modelo.** Nota, percentual, hora e contagem vêm do `plano.json`. Se o
   script não calculou, não entra no sumário. `conferir --sumario` existe para pegar isso.

2. **Importância é valor, não facilidade.** A nota 1–10 mede o quanto vale saber o tópico; o
   esforço só entra na *ordem da fila*. Um tópico de 8 horas que cai muito continua sendo 10.

3. **Pré-requisito antes do dependente, sempre.** A fila é topológica. Se a ordem parece errada,
   o defeito está no grafo — reporte, não reordene à mão.

4. **Estimativa vem marcada.** Duração que a skill estimou aparece com `~` no sumário e listada
   em `lacunas.md`. O leitor precisa saber o que é medição e o que é chute calibrado.

5. **Reprodutível.** Mesmo grafo, mesmos parâmetros, mesmo sumário. Grave o `sha256` do grafo no
   front-matter: é o que permite dizer, meses depois, que o plano nasceu de outra evidência.

6. **Não invente tópico.** O que não está no grafo não entra no sumário — vai para `lacunas.md`
   como "o edital cobre e o grafo não". Cobrir buraco com conhecimento próprio destrói a única
   garantia que este pipeline oferece.

7. **Não edite o grafo.** Divergência se relata; correção é trabalho de `mapear-conteudo`, sobre
   `evidencias.json`.

8. **Diga o tamanho da amostra.** "72% das questões" sobre 1.480 questões de 12 provas é um
   fato; sobre 40 questões de 2 provas é uma hipótese. O cabeçalho do sumário carrega os dois
   números, sempre.

9. **Aula cheia exige lastro.** Item sem 4 questões na amostra e sem 2% do share não recebe
   mais de 30 minutos: vira aula curta (se o edital exige ou algo depende dele) ou opcional em
   `omitidos`. Promover sem lastro exige `--sem-lastro` e o motivo declarado no sumário.

---

## Quando NÃO usar

- Não existe grafo do assunto → `mapear-conteudo` primeiro.
- Escrever a aula, as questões, os vídeos ou os flashcards → `apostila` e suas irmãs.
- Cronograma com datas ("quero passar em 12/out, 10h por semana") → fora de escopo por decisão
  de projeto; o sumário entrega ordem e horas, o calendário é do usuário.
- Reordenar um sumário já existente porque "não gostei da ordem" → ajuste o parâmetro
  (`--beta`, `--minutos-aula`) e recalcule, ou corrija o grafo. Editar o markdown à mão quebra a
  correspondência com o `plano.json` e o `conferir` acusa.

---

## Recursos

| arquivo | quando ler |
|---|---|
| `referencias/priorizacao.md` | as fórmulas, a escada 1–10, os parâmetros e como explicar uma nota |
| `referencias/anatomia-do-sumario.md` | a forma do `sumario.md`, o schema do `grade.json` e do `plano.json` |
| `referencias/dados-necessarios.md` | que campo do grafo alimenta que sinal, e o que acontece quando falta |
| `scripts/sumario.py` | `inspecionar` · `priorizar` · `conferir` |
| `scripts/ler_grafo.py` | o único arquivo que conhece o formato do grafo |
| `scripts/testes/test_sumario.py` | 46 testes; rode depois de mexer em qualquer script |

Saída em `sumarios/<slug>/`: `sumario.md` (documento), `plano.json` (cálculo, consumido pela
`apostila`), `grade.json` (as aulas nomeadas), `lacunas.md` (o que não dá para prometer).
