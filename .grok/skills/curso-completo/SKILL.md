---
name: curso-completo
description: >-
  Gera a apostila INTEIRA de um assunto, do zero: varre editais e provas, monta o sumário de
  estudo e produz TODAS as aulas em PDF (25–40 min cada), encadeando as skills
  `mapear-conteudo`, `montar-sumario` e `apostila` — cada aula escrita por um subagente
  `gerador-aula` e revisada por `revisor-aula`, em lotes de 3. Use quando o usuário disser
  "gera a apostila completa de X", "curso completo de X", "apostila de X do zero", "todas as
  aulas de X", "monta o material inteiro de X" ou apontar um sumário pedindo que todas as
  aulas sejam escritas. Retoma de onde parou. NÃO use para uma aula isolada ("gera a aula
  7") — isso é `apostila` + `revisar-aula`.
---

# Curso completo

Esta skill é um **orquestrador**: a sessão decide e despacha, os subagentes escrevem, os
scripts das skills donas validam. **Nada aqui reimplementa as skills encadeadas** — se um
passo parece precisar de lógica nova, ele está no lugar errado. A quantidade de aulas é a
que o conteúdo pedir: 5 ou 300, o critério é cobrir o assunto inteiro.

| fase | quem faz | entrada | saída | pronto quando |
|---|---|---|---|---|
| 0 estado | sessão | disco | ponto de entrada | anunciado em 3 linhas |
| 1 grafo | skill `mapear-conteudo` (sessão) | negociação com o usuário | `grafos/<slug>/` | `build` limpo |
| 2 sumário | skill `montar-sumario` (sessão) | `grafos/<slug>` | `sumarios/<slug>/` | `conferir` sai 0 |
| 3 anúncio | sessão | `plano.json` | tamanho do trabalho | anunciado, sem pergunta |
| 4 produção | `gerador-aula` depois `revisor-aula` | `sumarios/<slug>` + seq | só o PDF na pasta | 0 pendentes |
| 5 fechamento | sessão | os PDFs | relatório final | entregue |

---

## O procedimento

### 0. Ler o estado antes de gastar qualquer coisa

Primeiro comando, **sempre** — mesmo quando o usuário pede "do zero":

```bash
ls grafos/*/grafo.md sumarios/*/grade.json 2>/dev/null
python3 .grok/skills/curso-completo/scripts/progresso.py sumarios/<slug>   # se houver sumário
```

**O estado mora no disco, não na memória da sessão.** Não existe arquivo de estado próprio:
grafo, sumário e aulas prontas são três fatos, e cada um é a existência de um artefato. Um
curso de dezenas de aulas atravessa várias sessões — é esta fase que faz a reinvocação
continuar em vez de recomeçar. Anuncie em três linhas onde o pipeline está e por qual fase
vai entrar.

### 1. Grafo de incidência (`mapear-conteudo`)

- `grafos/<slug>/grafo.md` existe e o usuário não pediu atualização → **pule**, dizendo o
  que está sendo reaproveitado (escopo, banca, janela, confiança do `relatorio.md`).
- Senão → **invoque a skill `mapear-conteudo` e siga o procedimento dela inteiro.** É ela
  que negocia assunto, tipo, banca, janela e perfil com o usuário — não duplique a
  negociação aqui. Avise que esta é a fase longa (web, downloads, classificação).

Pronto quando: `grafos/<slug>/{grafo.md, evidencias.json, derivado.json, relatorio.md}`
existem e o `build` saiu limpo. Confiança global abaixo de 0,40: diga agora — contamina
todo o resto.

### 2. Sumário de estudo (`montar-sumario`)

- `sumarios/<slug>/grade.json` existe → só revalide:

```bash
python3 .grok/skills/montar-sumario/scripts/sumario.py conferir \
        --plano sumarios/<slug>/plano.json --grade sumarios/<slug>/grade.json \
        --sumario sumarios/<slug>/sumario.md
```

- Senão → **invoque a skill `montar-sumario` e siga o procedimento dela inteiro**
  (inspecionar → priorizar → escrever → conferir em laço). Parâmetros desta orquestração:
  `--assunto tudo` (o curso cobre o conteúdo inteiro, sem recorte) e `--minutos-aula 30`
  (o padrão — é o que põe as aulas na faixa 25–40 min).

Pronto quando: os quatro arquivos existem e `conferir` sai 0. **Nunca despache aula com
`conferir` reprovando** — a grade é o contrato de produção.

### 3. Anunciar o tamanho do trabalho (sem perguntar)

Com números lidos do `plano.json` (`totais.*`, `cobertura.marcos`) — nunca inventados:

```
Matemática Financeira — 17 tópicos, 62 aulas de 30 min, 31 h
  50% da prova nos 7 primeiros itens · 70% nos 11
  as aulas vão para aulas/matematica-financeira/
```

E **comece a produção direto**. Não há checkpoint de quantidade — decisão de projeto: o
conteúdo inteiro é o objetivo, a proteção é a retomada barata (o usuário pode interromper
quando quiser e reinvocar depois).

### 4. Produção em lotes de 3

Laço, até `progresso.py` não devolver pendente:

```bash
python3 .grok/skills/curso-completo/scripts/progresso.py sumarios/<slug> --pendentes --limite 3 --json
```

1. O comando devolve os próximos 3 seqs com o **diretório exato** de cada um.
2. Lote A: **3× `spawn_subagent` / `gerador-aula`** na mesma mensagem — diretórios
   disjuntos. Template em `referencias/orquestracao.md`.
3. Lote B, **depois que o A voltar**: **3× `revisor-aula`** nos mesmos diretórios.
   Grok não aninha subagente — o review não sai de dentro do gerador.
4. `progresso.py` de novo — **o disco é prova**. Pasta com só o PDF = pronta;
   fontes ainda lá = parcial. Uma linha por aula; despache o próximo lote.
5. Falha ou reprovação: registre e siga. No fim, **um** passe de reprocessamento
   (gerador com o `revisao.json` no prompt, depois revisor). O que sobrar fica pendente.
6. `CONFLITO`: nunca despache por cima — reporte e deixe a decisão com o usuário.

Pronto quando: `progresso.py` mostra 0 pendentes, ou o usuário mandou parar.

### 5. Fechamento

```bash
python3 .grok/skills/curso-completo/scripts/progresso.py sumarios/<slug>
```

- Liste os PDFs **na ordem da grade** (a saída do progresso já vem nessa ordem).
- Relate: total de aulas e horas prontas, cobertura acumulada, falhas remanescentes, e as
  lacunas herdadas de `sumarios/<slug>/lacunas.md` (2–3 linhas).
- Ofereça **uma vez** a importação de todos os flashcards no Anki:

```bash
python3 .grok/skills/flashcards-anki/scripts/anki_import.py aulas/<disciplina>/aula-NN-<slug>
```

(uma chamada por diretório de aula; é idempotente). Nunca dentro dos subagentes.

---

## Regras inegociáveis

1. **Esta skill não escreve aula, não calcula peso e não prioriza.** Só encadeia. Lógica
   própria só existe em `scripts/progresso.py`.
2. **Estado é o disco.** Rode `progresso.py` antes de todo despacho; nunca despache do que
   "você lembra que já fez".
3. **Um subagente por aula, um diretório por subagente.** Nunca dois no mesmo diretório.
4. **Só o PDF na pasta é o sinal de pronto.** O revisor fecha a aula com
   `fechar_aula.py`. HTML ou fontes no disco significam parcial.
5. **Falha de aula não derruba a apostila.** Relate e siga; a retomada resolve.
6. **Comandos com caminho literal**, sem `A=…`/`$A` — é o que casa com a lista de
   permissões e evita prompt no meio de um lote.
7. **Nenhum número inventado**: tudo que a sessão mostra ao usuário vem de `plano.json`,
   `grade.json` ou da saída dos scripts.
8. **Não edite `grafo.md`, `plano.json` nem HTML gerado.** Divergência se relata; correção
   é na skill dona.
9. **`--parcial` do `montar.py` é proibido no lote** — prévia sem páginas finais parece
   pronta no disco e engana quem for afrouxar a regra de pronto.

---

## Recursos

| arquivo | quando ler |
|---|---|
| `referencias/orquestracao.md` | template de despacho, política de lotes, falhas e retomada |
| `scripts/progresso.py` | estado por aula: grade.json × filesystem |
| `.grok/agents/gerador-aula.md` | escreve cada aula (grok-4.6) |
| `.grok/agents/revisor-aula.md` | double-check (grok-4.6) |
| `.grok/skills/revisar-aula/` | rubrica e contrato do `revisao.json` |
