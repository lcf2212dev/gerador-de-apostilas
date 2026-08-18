---
name: mapear-conteudo
description: >-
  Varre a internet atrás de editais e provas de concurso dos últimos 5 anos sobre um assunto,
  mapeia TODO o conteúdo programático e pondera cada tópico pela incidência real, produzindo
  `grafos/<slug>/grafo.md` — um grafo com pesos 0–100, classes A/B/C/D, pré-requisitos,
  tendência e confiança estatística, que `montar-sumario` e as skills de aula consomem para
  decidir o que priorizar. Use quando o usuário disser "mapeia o conteúdo de X", "o que mais cai
  em X", "gera o grafo de X", "varre as provas e editais de X", "quais assuntos priorizar em X",
  "monta o mapa de incidência de X", ou nomear um cargo/banca e perguntar o que estudar primeiro.
  Também para atualizar um grafo existente quando sai edital ou prova nova. NÃO monta cronograma
  nem sumário de estudo (isso é a skill `montar-sumario`) e NÃO escreve aulas. O `grafo.md`
  é derivado e nunca se edita à mão. Se existir `.env` com QConcursos, a skill `qconcursos`
  é a fonte primária de incidência.
---

# Mapear conteúdo

Produz um grafo ponderado do que cai num assunto de concurso, a partir de evidência coletada
na internet: editais (o que **pode** ser cobrado) e provas aplicadas (o que **é** cobrado).

O grafo existe porque o edital mente por omissão. Ele lista "Controle de Constitucionalidade" e
"Ordem Econômica" como dois itens de uma lista plana, quando um vale 12% da prova e o outro
0,4%. Quem estuda pelo edital distribui o esforço igualmente sobre coisas desiguais. O peso
desfaz isso — e as skills seguintes herdam a prioridade em vez de reinventá-la.

**Divisão de trabalho que sustenta a confiabilidade: o modelo extrai evidência, o script
calcula peso.** Nenhum número do grafo vem de julgamento; todos saem de fórmula determinística
sobre dados rastreáveis. É o que permite auditar, recalcular e discordar com fundamento.

Granularidade não é decisão desta skill. O grafo mapeia o conteúdo na estrutura que o edital e
as provas revelam; quantas aulas isso vira — 5 ou 300 — é problema de quem consome.

---

## O procedimento

### 1. Fixar o escopo

Determinar, perguntando ao usuário só o que não der para inferir:

- **assunto e tipo** — `disciplina` ("Direito Constitucional"), `cargo` ("Analista Judiciário
  do TRT") ou `area` ("TI para concursos"). Cargo abre em várias disciplinas; disciplina abre
  em temas.
- **banca-alvo** — muda o peso das provas de outras bancas. Sem banca definida, todas pesam igual.
- **órgão-alvo**, quando houver.
- **janela** — padrão 5 anos (2021–2026). O ano final é a referência do decaimento.
- **perfil** — padrão `profundo`: 8 editais, 30 provas. `padrao` = 5/15, `rapido` = 3/6.

```bash
S=.grok/skills/mapear-conteudo/scripts/grafo.py
python3 $S init <slug> --escopo "Direito Constitucional" --tipo disciplina \
        --banca FGV --janela 2021-2026 --perfil profundo --data <hoje>
```

### 2. Descobrir fontes

**Se `.env` tiver QConcursos**, comece pela skill `qconcursos` (`status` → `login` se
preciso → `raiox` / `questoes` / `editais` no recorte). Isso vale mais que dezenas de PDFs
porque a classificação por assunto já veio pronta. Sem `.env` ou login falho: registre
lacuna e siga.

Em paralelo: skill `pci-concursos` no cargo/órgão/banca da janela, e `WebSearch` com as
consultas de `references/fontes.md`, nesta ordem: órgão-alvo → banca-alvo → cargo
equivalente em outros órgãos → disciplina solta. Diversificar órgãos: dez provas do mesmo
concurso medem aquele concurso, não a disciplina.

Montar a lista de candidatos e deduplicar por (órgão, banca, ano, cargo) antes de baixar
qualquer coisa.

### 3. Coletar

Do QC: saídas de `qc.py` viram fonte `tipo: plataforma` (Raio X agregado) e/ou `questoes[]`
com `fonte` apontando para a URL acessada. Editais/PDFs que a conta baixar entram como
`tipo: edital` ou `prova`.

Cadernos públicos: skill `pci-concursos` (`buscar` no cargo/órgão/banca da janela,
depois `baixar` os que couberem no perfil). Cada PDF vira fonte `tipo: prova` com
`url` acessada, `sha256`, `acessado_em`. Gabarito definitivo no mesmo lote.

Outras URLs diretas: `curl` → `pdftotext -layout` → `.txt` em `grafos/<slug>/fontes/`.
Conferir com `file`, guardar `sha256`. Detalhes: `references/extracao.md`.
Dono do QC: skill `qconcursos`. Dono do PCI: skill `pci-concursos`.

### 4. Extrair a taxonomia (editais)

O conteúdo programático dos editais vira a árvore de nós. **Cobertura total**: todo item do
anexo existe como nó, inclusive o que nunca caiu. Unificar rótulos divergentes entre editais em
um nó só, com os variantes em `sinonimos`.

Esta fase vem **antes** da próxima, sempre. Sem a lista fechada de ids, cada prova gera rótulos
próprios e o grafo vira um amontoado de sinônimos.

### 5. Classificar as questões (provas)

Um registro por questão: `{fonte, n, nos, tipo, dificuldade}`. Classificar no nó **mais
específico** que a questão exige — jogar tudo no tema pai destrói a resolução do grafo.
Questão que cobre dois assuntos lista os dois; o script divide.

É o gargalo do processo e o único ponto que justifica paralelizar: um subagente por prova
(só da sessão principal — Grok não aninha), com a taxonomia fechada no prompt (modelo em
`references/extracao.md`). Itens já classificados pelo QC não precisam dessa passagem.

### 6. Declarar as relações

- `prerequisito` — o que precisa vir antes. É o que dá ordem ao plano de estudos e **precisa
  formar um DAG**.
- `atualiza` — lei nova que substitui a antiga (8.666 → 14.133).
- `correlato` — reforço mútuo sem ordem.

`contem` e `coocorre` são derivadas pelo script. Declará-las é erro de validação.

### 7. Construir e auditar

```bash
python3 $S validar <slug> && python3 $S build <slug>
```

`validar` bloqueia o build por fonte sem URL ou data, ciclo em pré-requisito, id órfão,
edital que nenhum nó menciona. Nenhum peso é escrito à mão em momento algum.

Depois, escrever `grafos/<slug>/relatorio.md` e responder ao usuário com: as 15 folhas de maior
peso, a confiança global, a cobertura editalícia, o que falhou na coleta e qual lacuna isso
deixa. Se a confiança global ficar abaixo de 0.40, dizer isso na cara — o grafo serve para
orientar, não para decidir, enquanto a amostra for essa.

---

Use grok-4.6. Sem troca de modelo no meio.

---

## As regras inegociáveis

1. **Nenhum número sem fonte rastreável.** Toda questão contada aponta para uma fonte com URL
   acessada e data de acesso. A validação reprova o que não tiver.
2. **Nunca inventar URL.** Só entra o endereço efetivamente acessado. URL deduzida de um padrão
   não é fonte.
3. **Falha é falha.** PDF que não baixou ou não converteu entra como `status: "falha"` e fica
   de fora do cálculo. Jamais estimar o conteúdo de uma fonte que não foi lida.
4. **Cobertura editalícia total.** Todo item do conteúdo programático vira nó, mesmo com
   incidência zero. O grafo pondera o conteúdo inteiro; não o recorta.
5. **Amostra fraca se declara.** Poucas provas viram confiança baixa explícita e lacuna
   registrada — nunca um peso confiante encobrindo a ignorância.
6. **`grafo.md` é derivado.** Ajuste vai em `evidencias.json` ou `ajustes.json` e passa por
   `build`. Editar o `.md` é perder a alteração no próximo build.
7. **Ids são estáveis.** Um item novo ganha id novo; nunca renumerar ids já publicados, porque
   as skills consumidoras referenciam por id.

---

## Atualizar um grafo existente

Saiu edital ou prova nova: acrescentar as fontes e os registros em `evidencias.json`, atualizar
`janela.ate` se o ano virou, e rodar `validar && build`. Os pesos se reequilibram sozinhos — o
decaimento por recência faz o material antigo perder força sem que nada seja apagado.

---

## Quando NÃO usar

- Montar cronograma, sumário ou ordem de estudo → skill `montar-sumario` (consome este grafo).
- Escrever aula, apostila, questões ou flashcards → skills de aula.
- Responder "o que cai em X" de memória, sem coletar nada → esta skill existe justamente para
  não fazer isso; se o usuário quer só um palpite rápido, diga que é palpite.
- Assunto que não é de concurso público brasileiro — o modelo de pesos assume edital com
  conteúdo programático e provas objetivas recorrentes.

---

## Recursos

| arquivo | quando ler |
|---|---|
| `references/esquema.md` | formato de `evidencias.json`, `ajustes.json` e `grafo.md`, campo a campo |
| `references/pesos.md` | fórmulas, calibração dos parâmetros e um exemplo numérico conferível |
| `references/fontes.md` | onde achar editais e provas, domínios das bancas, buscas que funcionam |
| `references/extracao.md` | comandos de download e conversão, edital → taxonomia, prova → questões |
| `scripts/grafo.py` | `init` · `validar` · `build` · `consultar` · `no` · `ordem` · `resumo` |
| skill `pci-concursos` | caderno e gabarito em PDF no PCI |

Saída em `grafos/<slug>/`: `grafo.md` (canônico), `evidencias.json` (fonte da verdade),
`derivado.json` (para consumo por script), `relatorio.md`, `fontes/` (PDFs e textos).
