# Esquema — `evidencias.json` e `grafo.md`

Contrato entre esta skill e quem consome o grafo. `evidencias.json` é o que se escreve;
`grafo.md` é o que sai. Nunca o contrário.

---

## 1. `evidencias.json` — a entrada

Fonte da verdade. Contém apenas **observações rastreáveis**: o que estava no edital, o que
caiu na prova, onde isso foi lido. Nenhum peso, classe ou prioridade aparece aqui — esses
são calculados.

```jsonc
{
  "schema": "grafo-concurso/1",

  "escopo": {
    "slug": "direito-constitucional",     // nome do diretório em grafos/
    "rotulo": "Direito Constitucional",
    "tipo": "disciplina",                 // disciplina | cargo | area
    "banca_alvo": ["FGV"],                // [] = todas as bancas pesam igual
    "orgaos_alvo": ["TJ-SP", "TRT"],      // informativo
    "janela": {"de": 2021, "ate": 2026},  // 'ate' é o ano de referência do decaimento
    "perfil": "profundo",                 // rapido | padrao | profundo
    "gerado_em": "2026-08-17"
  },

  "parametros": {},                       // sobrescreve PADROES de grafo.py; {} usa tudo padrão

  "fontes": [ /* ver 1.1 */ ],
  "nos":    [ /* ver 1.2 */ ],
  "questoes":[ /* ver 1.3 */ ],
  "arestas": [ /* ver 1.4 */ ],
  "lacunas": [ /* ver 1.5 */ ]
}
```

### 1.1 `fontes[]` — de onde veio cada número

Toda evidência aponta para uma fonte. Sem `url` e `acessado_em`, a validação falha: um número
sem procedência não entra no grafo.

| campo | obrigatório | valores |
|---|---|---|
| `id` | sim | `E01`, `P07`, `Q02` — prefixo livre, único |
| `tipo` | sim | `edital` · `prova` · `plataforma` |
| `banca` | sim (na prática) | `FGV`, `Cebraspe`, `FCC`… — comparação ignora acento e caixa |
| `orgao` | recomendado | `TJ-SP`, `TRT-2` |
| `ano` | sim | inteiro; fora da janela → ignorada no cálculo, com aviso |
| `cargo` | recomendado | `Analista Judiciário` |
| `url` | **sim** | a URL efetivamente acessada; nunca uma URL presumida |
| `acessado_em` | **sim** | `AAAA-MM-DD` |
| `status` | não | `ok` (padrão) · `parcial` · `falha` — `falha` não entra no cálculo |
| `sha256` | não | do PDF baixado, para reprodutibilidade |
| `n_questoes_escopo` | não | quantas questões da prova pertencem ao escopo |
| `plataforma` | se `tipo: plataforma` | `qconcursos`, `tecconcursos` |
| `obs` | não | por que falhou, o que faltou |

### 1.2 `nos[]` — o conteúdo

| campo | obrigatório | notas |
|---|---|---|
| `id` | sim | estável e único. **É a chave pública** — consumidores referenciam por `id`, nunca por rótulo |
| `rotulo` | sim | nome legível, normalizado entre editais |
| `nivel` | sim | `escopo` · `bloco` · `disciplina` · `tema` · `topico` · `subtopico` |
| `pai` | sim, exceto na raiz | `null` só na raiz |
| `origem` | sim | `["edital"]`, `["prova"]` ou ambos |
| `mencao` | se `origem` inclui edital | `{"E01": "explicita", "E03": "generica"}` |
| `editais` | alternativa | `["E01","E03"]` — forma curta, equivale a `explicita` |
| `custo_h` | recomendado | horas estimadas para dominar; alimenta o ROI. Padrão 1.0 |
| `tipo_cobranca` | recomendado | `letra-de-lei`, `jurisprudencia`, `doutrina`, `calculo`, `interpretacao`, `memorizacao`, `pratica` |
| `sinonimos` | não | como o mesmo item aparece em outros editais |
| `obs` | não | legislação de referência, ressalva |

`explicita` = o edital nomeia o item. `generica` = está coberto por uma cláusula guarda-chuva
("noções de…", "e legislação correlata"), e vale metade.

### 1.3 `questoes[]` — o que caiu

Um registro por questão observada.

```jsonc
{"fonte": "P07", "n": 23, "nos": ["DC.03.02"], "tipo": "jurisprudencia",
 "dificuldade": 3, "obs": "STF Tema 885"}
```

- `nos` com mais de um id: a questão é **dividida** entre eles (`1/k` para cada), nunca contada
  inteira em ambos.
- `peso` (opcional, padrão 1): usado para **registro agregado** — quando a fonte informa
  "47 questões deste assunto" em vez de listar uma a uma. Nesse caso marque `"agregada": true`,
  o que exclui o registro do cálculo de coocorrência (não há questão individual para cruzar).

```jsonc
{"fonte": "T01", "nos": ["DC.03"], "peso": 47, "agregada": true}
```

### 1.4 `arestas[]` — as relações declaradas

Só três tipos se declaram. `contem` e `coocorre` são **derivadas** pelo script; declará-las é erro.

| tipo | direção | força | para que serve |
|---|---|---|---|
| `prerequisito` | `de` vem antes de `para` | 0.3 sugerido … 1.0 obrigatório | ordena o plano de estudos. **Precisa formar um DAG** |
| `correlato` | simétrico na prática | 0.0–1.0 | conteúdos que se reforçam |
| `atualiza` | `de` é substituído por `para` | 1.0 | mudança legislativa (Lei 8.666 → 14.133) |

### 1.5 `lacunas[]` — o que não deu para saber

```jsonc
{"o_que": "Nenhuma prova FGV de 2025 localizada",
 "impacto": "tendência do último ano subestimada"}
```

Registrar lacuna é obrigatório quando a coleta ficou aquém do perfil. Elas aparecem na seção 6
do `grafo.md` — é o que separa um grafo honesto de um grafo que finge completude.

---

## 2. `ajustes.json` — override manual (opcional)

Para corrigir o que a fórmula não sabe. Todo override é marcado com flag no grafo, para que a
auditoria continue possível.

```jsonc
{
  "parametros": {"w_incidencia": 0.75},
  "nos": {
    "DC.03.02": {"custo_h": 4.0, "nota": "exige leitura de jurisprudência"},
    "DC.07.01": {"peso_manual": 95, "classe_manual": "A",
                 "nota": "mudança legislativa recente ainda não refletida nas provas"}
  }
}
```

`peso_manual` e `classe_manual` saem da fórmula e recebem as flags `peso-manual` /
`classe-manual`. Usar com parcimônia: cada override é um ponto onde o grafo deixa de ser
auditável.

---

## 3. `grafo.md` — a saída

Gerado por `grafo.py build`. **Nunca editar à mão** — o próximo build sobrescreve.

Frontmatter YAML com escopo, janela, `ano_ref`, contagem de fontes, `cobertura_edital`,
`confianca_global` e os parâmetros usados. Corpo em 8 seções: como ler · prioridades · nós ·
arestas · mapa mermaid · lacunas · fontes · contrato de consumo.

Acima de 250 nós (parâmetro `max_nos_arquivo_unico`), a seção 3 vira um agregado por disciplina
e as tabelas completas saem em `grafo/<disciplina>.md`.

### 3.1 Campos por nó (garantidos)

| campo | faixa | significado |
|---|---|---|
| `id`, `rotulo`, `nivel`, `pai` | — | identidade e posição |
| `peso` | 0–100 | prioridade **dentro do nível**. Não compare tópico com disciplina |
| `classe` | A · B · C · D | faixa de Pareto do nível |
| `share_pct` | 0–100 | fatia da carga total de questões do escopo |
| `n_questoes` | ≥ 0 | tamanho da amostra (soma do ramo) |
| `edital` | 0–1 | fração ponderada dos editais que cobram o item |
| `tendencia` | `alta` · `estavel` · `queda` · `indefinida` | |
| `confianca` | 0–1 | abaixo de 0.30, o peso é hipótese |
| `custo_h` | > 0 | horas estimadas |
| `roi` | 0–100 | `peso / custo_h`, normalizado por nível |
| `tipo_cobranca` | lista | como a banca cobra |
| `origem` | lista | `edital`, `prova` |
| `flags` | lista | `promover_se_confirmado`, `piso-edital`, `peso-manual`, `classe-manual` |
| `incidencia_norm`, `incidencia_ajustada` | 0–1 | antes e depois do encolhimento; para auditoria |

`derivado.json` sai ao lado com exatamente esses dados em JSON — é o que `consultar --json` lê.

---

## 4. Como as skills consumidoras devem ler

Por script, não parseando markdown:

```bash
python3 .claude/skills/mapear-conteudo/scripts/grafo.py consultar <slug> --classe A --classe B --folhas --json   # o que priorizar
python3 .claude/skills/mapear-conteudo/scripts/grafo.py ordem <slug> --folhas --json                             # em que ordem estudar
python3 .claude/skills/mapear-conteudo/scripts/grafo.py no <slug> DC.03.02 --json                                # ficha + vizinhança
python3 .claude/skills/mapear-conteudo/scripts/grafo.py resumo <slug> --json                                     # confiabilidade do grafo
```

Três regras para quem consome:

1. **Referenciar por `id`.** Rótulos mudam quando um edital novo renomeia o item; ids não.
2. **Respeitar `confianca`.** Um nó com `confianca < 0.30` não sustenta decisão forte — trate
   o peso como hipótese e diga isso ao usuário.
3. **Comparar só dentro do mesmo `nivel`.** Peso 100 de tópico e peso 100 de disciplina não
   significam a mesma coisa.
