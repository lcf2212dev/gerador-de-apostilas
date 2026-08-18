# Catálogo de fontes

Sites mudam de estrutura sem avisar. Este catálogo diz **onde procurar e como cada fonte
costuma quebrar** — não é uma lista de URLs para colar. As URLs marcadas ✅ foram verificadas
em 2026-08-17; as demais são pontos de partida a confirmar em execução.

> **Regra de ouro:** só entra em `evidencias.json` a URL que foi **efetivamente acessada**, com
> a data do acesso. URL presumida a partir de um padrão ("deve ser /provas/2024/…") não é fonte.
> Se o download falhou, registre `status: "falha"` e siga — nunca estime o conteúdo.

---

## 1. Editais — a taxonomia oficial

O edital dá a espinha dorsal do grafo: o conteúdo programático é a lista fechada do que pode
ser cobrado. Procure o **"Anexo II — Conteúdo Programático"** (padrão de mercado; alguns órgãos
usam "Anexo 2", "Anexo III" ou "Dos Conteúdos Programáticos"). ✅

Onde os PDFs ficam:

| origem | padrão observado |
|---|---|
| Site da banca | ✅ `conhecimento.fgv.br/sites/default/files/concursos/*.pdf` — PDF direto, sem intermediária |
| Portal do concurso | ✅ subdomínio por certame, ex.: `<ano><sigla>.fepese.org.br/?arquivo=…&go=download` |
| Site do órgão | seção "Concursos" ou "Editais"; frequentemente `wp-content/uploads/<ano>/<mês>/` |
| Agregadores | ✅ `estudegratis.com.br` traz edital junto da prova; `pciconcursos.com.br` na página do concurso |

Retificações importam: um edital retificado muda o conteúdo programático. Buscar
`"retificação" edital <órgão> <ano>` antes de fechar a taxonomia.

## 2. Provas — a incidência real

| fonte | o que serve | como quebra |
|---|---|---|
| ✅ `pciconcursos.com.br/provas/` via skill `pci-concursos` | caderno + gabarito em PDF, por cargo/órgão/banca | o link da tabela **não** é o PDF: `pci.py baixar <slug>` faz o pulo `/provas/download/` |
| ✅ `estudegratis.com.br/provas` | ~42 mil provas, card com Prova + Gabarito + Edital | paginação profunda; slug no formato `prova-<cargo>-<orgao>-<ano>` |
| ✅ `provasbrasil.com.br` | recortes por banca e por disciplina | cobertura irregular por ano |
| ✅ `veprovas.com.br` | provas com gabarito das bancas grandes | catálogo menor |
| Site da própria banca | versão canônica, com gabarito definitivo | some quando o certame encerra; nem toda banca mantém acervo |

Preferir sempre o **caderno oficial da banca** quando existir: agregadores às vezes hospedam
versões preliminares, sem as anulações.

O **gabarito definitivo** importa mais do que parece — questão anulada não deve contar como
incidência. Quando houver, cruze com a lista de anulações e registre em `obs`.

## 3. Incidência já classificada (atalho de alta precisão)

Estas plataformas já classificam cada questão por assunto. **QConcursos autenticado** (skill
`qconcursos`, `.env`) vale mais que dezenas de PDFs e é a fonte primária quando o login sobe.

| fonte | o que oferece |
|---|---|
| ✅ `qconcursos.com` via `qc.py` | Raio X, questões classificadas, videoaulas, editais — o que a conta libera |
| ✅ `tecconcursos.com.br` | filtro avançado com percentual por assunto, banca, ano e área |
| ✅ `tecconcursos.com.br/blog/noticias/…` | série pública "10 assuntos mais cobrados…", com n e percentual — sem login |

Registrar Raio X como `tipo: "plataforma"` e **agregado** (`peso: N, agregada: true`). Itens
individuais do `qc.py questoes` entram um a um. A taxonomia da plataforma raramente coincide
com a do edital: mapear e anotar em `obs`.

Sem `.env` ou login falho: fontes públicas + lacuna. Não contornar paywall.

## 4. Bancas — domínios oficiais ✅

Confirmados em 2026-08-17. Servem para achar o acervo próprio de provas e os editais canônicos.

| banca | domínio | estilo que a prova costuma ter |
|---|---|---|
| Cebraspe (ex-Cespe) | `cebraspe.org.br` | certo/errado, penaliza erro; enunciados que generalizam |
| FGV | `conhecimento.fgv.br` | múltipla escolha, enunciado longo, caso concreto |
| FCC | `concursosfcc.com.br` · `fcc.org.br` | literalidade da lei, alternativas próximas |
| Vunesp | `vunesp.com.br` | direta, forte em interpretação de texto |
| Cesgranrio | `cesgranrio.org.br` | contextualizada, boa carga de cálculo |
| IBFC | `ibfc.org.br` | objetiva, cobrança direta |
| Instituto AOCP | `institutoaocp.org.br` | — |
| Quadrix | `quadrix.org.br` | conselhos de classe |
| Consulplan | `institutoconsulplan.org.br` | — |
| IADES | `iades.com.br` | — |
| FEPESE | `fepese.org.br` | concursos de SC |

O estilo da banca não entra na fórmula, mas orienta o campo `tipo_cobranca` dos nós — que é o
que a skill de aulas usa para decidir como ensinar.

## 5. Buscas que funcionam

Montar as consultas com o vocabulário que os sites realmente usam:

```
edital <órgão> <ano> "conteúdo programático" filetype:pdf
edital <órgão> <cargo> <ano> anexo II conteúdo programático
prova <cargo> <órgão> <banca> <ano> gabarito pdf
<banca> <disciplina> assuntos mais cobrados últimos 5 anos
caderno de questões <órgão> <ano> <cargo> tipo 1
retificação edital <órgão> <ano>
```

Estratégia de cobertura, em ordem:

1. **Pelo órgão-alvo** — todos os certames dele na janela; é o que melhor prevê.
2. **Pela banca-alvo** — mesma banca, órgãos parecidos, mesmo nível de escolaridade.
3. **Pelo cargo** — cargo equivalente em outros órgãos, para engrossar a amostra.
4. **Pela disciplina** — quando o escopo é uma disciplina solta, sem cargo definido.

Diversificar órgãos importa: 10 provas do mesmo concurso repetido medem aquele concurso, não a
disciplina.

## 6. O que não usar como evidência

- **Apostilas e cursinhos** — dizem o que é importante, mas é opinião, não contagem. Podem
  sugerir pré-requisitos; nunca alimentar `questoes[]`.
- **Listas de "assuntos que mais caem" sem número** — post de blog sem n nem período não é dado.
- **Resumos de IA e agregadores de agregador** — sem rastreabilidade até o caderno original.
- **Provas de nível diferente** — prova de nível médio não mede a incidência de um cargo de
  nível superior, mesmo na mesma disciplina.
- **Simulados** — não são prova aplicada.

## 7. Quantas fontes bastam

| perfil | editais | provas | quando usar |
|---|---|---|---|
| `rapido` | 3 | 6 | esboço, escopo estreito, teste |
| `padrao` | 5 | 15 | uso normal |
| `profundo` | 8 | 30 | **padrão desta skill** — cauda longa confiável |

Abaixo de 5 provas úteis, `grafo.py validar` emite aviso e a confiança global cai — o grafo
ainda é gerado, mas dizendo o que não sabe.
