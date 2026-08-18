# Anatomia do sumário

A forma dos quatro arquivos de `sumarios/<slug>/`. O `plano.json` sai do script; `sumario.md`,
`grade.json` e `lacunas.md` são escritos pelo modelo **a partir dele** — e conferidos contra ele.

---

## `sumario.md`

### Front-matter

Existe para que qualquer número possa ser refeito meses depois:

```yaml
---
assunto: Direito Constitucional
grafo: grafos/trf-constitucional/grafo.md
grafo_sha256: a80d5e8a8b9950fd…
banca_alvo: [FGV]
janela: 2021-2026
questoes_analisadas: 1480
itens: 17
aulas: 62
aulas_curtas: 2
opcionais: 1
horas: 31.0
importancia_media: 4.94
parametros: {beta: 0.35, gama: 1.0, minutos_aula: 30, coesao: 0.15}
gerado_em: 2026-08-17
skill: montar-sumario 1.0.0
---
```

### Corpo

````markdown
# Sumário — Direito Constitucional · banca FGV

17 tópicos · 31 h · 62 aulas de 30 min · importância média 4,9/10
Base: 1.480 questões de 12 provas (2021–2026), confiança global 0,83.

**Por onde começar:** *Objetivos e fundamentos da República* abre a fila mesmo valendo 2,8% das
questões — é pré-requisito dos direitos do art. 5º, que sozinhos valem 14,1% e destravam outros
quatro tópicos. Os 7 primeiros itens cobrem metade da prova.

## Módulo 1 — Direitos e Garantias Fundamentais            ★★★☆☆  média 5,4/10

| # | tópico | importância | prova | esforço | pré-requisito |
|---|---|---|---|---|---|
| 1.1 | Direitos individuais (art. 5º) | **10/10** | 14,1% · 209 q | 3 h · 6 aulas | — |
| 1.2 | Direitos políticos e partidos | **5/10** | 5,4% · 80 q | 1,5 h · 3 aulas | — |
| 1.3 | Remédios constitucionais | **5/10** | 6,4% · 95 q | 2 h · 4 aulas | 1.1 |
| 1.4 | Disposições transitórias | **1/10** | 0,0% · 0 q | 30 min · 1 aula curta · sem lastro (0 q) | — |

## Módulo 2 — Organização dos Poderes                      ★★★☆☆  média 4,5/10

…

## Fila de estudo

A ordem respeita os pré-requisitos; entre os liberados, vem primeiro o de maior retorno por hora.

| ordem | item | tópico | nota | acumulado |
|---|---|---|---|---|
| 1 | 5.1 | Objetivos e fundamentos da República | 6/10 | 2,8% |
| 2 | 1.1 | Direitos individuais (art. 5º) | 10/10 | 16,9% |
| 3 | 3.1 | Entes federativos e federação | 5/10 | 21,4% |

## Cobertura acumulada

```
 7 primeiros itens  ▓▓▓▓▓░░░░░  51,4%
11 primeiros itens  ▓▓▓▓▓▓▓░░░  76,8%
14 primeiros itens  ▓▓▓▓▓▓▓▓▓░  92,5%
```

## Como ler a nota

A importância é o valor do tópico em décimos do valor do tópico mais forte **deste recorte**, e
combina o quanto ele cai (com decaimento por ano e peso da banca-alvo) com o quanto ele destrava
do resto do edital. Esforço não entra na nota — só na ordem da fila.

| nota | significa |
|---|---|
| 10 | o topo do recorte — núcleo absoluto, cai em praticamente toda prova |
| 8–9 | 80–90% do valor do topo — alta incidência ou destrava boa parte do edital |
| 6–7 | 60–70% — cobrança regular e previsível |
| 4–5 | 40–50% — aparece de vez em quando, vale uma passada |
| 2–3 | 20–30% — raro; só depois que o núcleo estiver dominado |
| 1 | 10% ou menos — marginal, ou fora do edital-alvo |

> Ressalvas em [`lacunas.md`](lacunas.md). Números derivados de
> `grafos/trf-constitucional/grafo.md` — para recalcular, rode a skill de novo, não edite aqui.
````

### O que o modelo decide, e o que ele copia

**Copia do `plano.json`, sem tocar:** notas, percentuais, contagens de questão, horas, número de
aulas, ordem da fila, acumulados, módulos e seus membros.

**Decide:** o título de cada módulo (o rótulo do grafo costuma servir; um nome melhor é bem-vindo
desde que o `id` continue rastreável), o parágrafo "por onde começar", onde vale observar que um
tópico grande será dividido por assunto e não por relógio, e quais duas ou três ressalvas merecem
subir do `lacunas.md` para o corpo.

**Marcações obrigatórias na tabela:**

| marca no item | escreva assim |
|---|---|
| `custo-estimado` | `~3 h` (til antes da duração) |
| `confianca-baixa` | `6/10 ⚠` e uma nota de rodapé: amostra pequena, trate como hipótese |
| `importado` | módulo 0, com a frase "vem de fora do assunto, mas é pré-requisito" |
| `sem-lastro` | na coluna de esforço: `30 min · 1 aula curta · sem lastro (0 q)`; item `formato: "opcional"` não entra na grade — vai para `omitidos` com o `motivo_omissao` do plano |
| `promover_se_confirmado` e outras flags do grafo | cite a flag entre parênteses |

Estrela no cabeçalho do módulo é decoração derivada da média (`★ = nota/2`), nunca uma segunda
escala. Se atrapalhar, tire — a nota é que manda.

---

## `grade.json` — as aulas nomeadas

Uma linha por aula (o `plano.json` tem uma linha por *item*; um item de 3 h vira 6 aulas):

```json
{
  "assunto": "Direito Constitucional",
  "plano": "sumarios/trf-constitucional/plano.json",
  "gerado_em": "2026-08-17",
  "aulas": [
    {
      "id": "5.1-1",
      "seq": 1,
      "item": "5.1",
      "titulo": "Fundamentos da República: soberania, cidadania e dignidade",
      "objetivo": "Identificar os cinco fundamentos do art. 1º e distinguir fundamento de objetivo",
      "modulo": 5,
      "minutos": 30,
      "importancia": 6,
      "formato": "cheia",
      "nivel": "basico"
    }
  ],
  "omitidos": [
    {"num": "5.2", "motivo": "1,1% da prova e confiança 0,28 — fora do recorte"},
    {"num": "5.3", "motivo": "opcional: 0 questões na amostra, sem exigência de edital, não destrava item cheio", "formato": "opcional"}
  ]
}
```

| campo | de onde vem |
|---|---|
| `id` | `<num do item>-<parte>` |
| `seq` | posição global da aula, 1..N, na ordem da fila |
| `item`, `modulo`, `importancia`, `formato` | do `plano.json`, sem alterar |
| `minutos` | a fatia correspondente de `minutos_por_aula` — a soma tem que bater com `minutos` do item |
| `titulo`, `objetivo`, `nivel` | escritos pelo modelo |

Item `formato: "opcional"` não vira aula: copie-o para `omitidos` com o `motivo_omissao` do
plano (o registro em `omitidos` aceita `{"num", "motivo", "formato": "opcional"}`).

`conferir` reprova: item sem aula e sem `omitidos`, soma de minutos divergente, número de aulas
diferente do plano, importância alterada, ordem que viola pré-requisito, aula curta que virou
mais de uma aula e item `opcional` fora de `omitidos`.

---

## `plano.json` — o cálculo

Emitido por `sumario.py priorizar`. Blocos: `grafo` (origem, sha256, escopo, banca, janela),
`assunto`, `parametros`, `totais`, `escada`, `modulos`, `itens`, `fila`, `cobertura`, `lacunas`.

Cada item traz:

```json
{
  "num": "1.1", "seq": 2, "id": "dc-dir-ind", "rotulo": "Direitos individuais (art. 5º)",
  "nivel": "topico", "modulo": 1, "importancia": 10, "valor": 1.0,
  "componentes": {"base": 1.0, "centralidade": 0.792, "peso_grafo": 100.0,
                  "share_pct": 14.12, "edital": 1.0, "tendencia": "estavel", "confianca": 0.95},
  "classe_grafo": "A", "n_questoes": 209.0, "share": 0.1412, "share_do_grafo": 0.1412,
  "formato": "cheia",
  "minutos": 180, "horas": 3.0, "aulas": 6, "minutos_por_aula": [30, 30, 30, 30, 30, 30],
  "roi": 0.333, "requer": [], "destrava": ["dc-dir-rem", "dc-dir-soc"],
  "tipo_cobranca": ["letra-lei", "jurisprudencia"], "marcas": [], "obs": ""
}
```

O `formato` (`cheia`/`curta`/`opcional`) é a regra de lastro aplicada; item `opcional` traz
também `motivo_omissao`, pronto para copiar aos `omitidos` da grade. **Compatibilidade:** o
campo novo é opcional — consumidor antigo pode ignorá-lo — e nenhum campo existente se
renomeia.

**Este é o arquivo que a skill `apostila` lê.** `contexto_aula.py` usa `seq`, `num`, `id`,
`rotulo`, `minutos_por_aula`, `importancia`, `classe_grafo`, `share`, `n_questoes`,
`tipo_cobranca`, `marcas`, `formato`, `requer`, `destrava`, `modulo` e `obs`, mais
`grafo.escopo` e `grafo.banca_alvo`. Nenhum desses campos se renomeia sem avisar a skill de
aulas.

> Detalhe de uso: chame `contexto_aula.py` com `--seq` ou `--id`. O `--num` dele espera inteiro,
> e o `num` daqui é hierárquico (`"1.2"`).

---

## `lacunas.md`

O bloco `lacunas` do plano, em prosa curta. Uma seção por tipo, e cada uma responde "o que isso
impede de prometer":

```markdown
# Lacunas — Direito Constitucional

## Sinais desligados
Nenhum. Incidência, recência, banca, edital, centralidade e esforço vieram todos do grafo.

## Confiança frágil (1 item)
- **5.2 Relações internacionais** — confiança 0,28, 16 questões. A nota 2/10 é hipótese.

## Custo estimado (0 itens)
Todas as durações vieram do grafo.

## Herdado do grafo
- Prova de 2026 ainda não catalogada — a janela cobre 2021–2025 de fato.

## O que este sumário não cobre
3,4% das questões do escopo ficaram fora do recorte pedido.
```
