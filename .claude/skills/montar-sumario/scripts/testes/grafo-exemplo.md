---
schema: grafo-concurso/1
escopo: Direito Constitucional
slug: direito-constitucional-exemplo
tipo_escopo: disciplina
banca_alvo: [FGV]
orgaos_alvo: [TRF]
janela: 2021-2026
ano_ref: 2026
perfil: profundo
gerado_em: 2026-08-17
fontes: {editais: 3, provas: 12, plataformas: 2, falhas: 0}
questoes: 1480
nos: 23
cobertura_edital: 0.94
confianca_global: 0.83
parametros: {w_incidencia: 0.65, w_edital: 0.35, meia_vida_anos: 2.5, peso_banca_alvo: 1.0, peso_outras_bancas: 0.45, k_confianca: 5.0, m_prior_ramo: 5.0}
---

# Grafo de conteúdo ponderado — Direito Constitucional

> **FIXTURE DE TESTE.** Números inventados para exercitar `sumario.py`. Não use para estudar:
> nenhuma prova real foi lida para montar este arquivo. O formato imita o que a skill
> `mapear-conteudo` renderiza, para que os testes falhem se o contrato mudar.

## 1. Como ler

- **peso (0–100)** — prioridade relativa, normalizada **dentro de cada nível**.
- **classe** — **A** concentra os primeiros 50% da carga, **B** até 80%, **C** até 95%, **D** o resto.
- **share%** — fatia da carga total de questões do escopo.

## 2. Prioridades

| # | id | tópico | peso | classe | share% | n_q | tend | conf |
|---|---|---|---|---|---|---|---|---|
| 1 | dc-dir-ind | Direitos individuais (art. 5º) | 100 | A | 14.12 | 209 | estavel | 0.95 |
| 2 | dc-con-conc | Controle concentrado (ADI, ADC, ADPF) | 82 | A | 11.22 | 166 | alta | 0.92 |
| 3 | dc-org-adm | Administração pública (arts. 37–41) | 74 | A | 9.80 | 145 | estavel | 0.90 |
| 4 | dc-pod-jud | Poder Judiciário | 63 | A | 8.38 | 124 | estavel | 0.88 |
| 5 | dc-pod-leg | Poder Legislativo | 55 | B | 6.89 | 102 | estavel | 0.86 |

## 3. Nós

| id | rótulo | nível | pai | peso | classe | share% | n_q | edital | tendência | confiança | custo_h | roi | cobrança | origem | flags |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| dc | Direito Constitucional | disciplina | — | 100 | A | 100.00 | 1480 | 1.00 | estavel | 0.83 | 31.5 | 3.2 | letra-lei/jurisprudencia | edital+prova |  |
| dc-dir | Direitos e Garantias Fundamentais | tema | dc | 100 | A | 33.85 | 501 | 1.00 | estavel | 0.91 | 9.5 | 10.5 | letra-lei/jurisprudencia | edital+prova |  |
| dc-pod | Organização dos Poderes | tema | dc | 72 | A | 24.26 | 359 | 1.00 | estavel | 0.85 | 8.5 | 8.5 | letra-lei | edital+prova |  |
| dc-org | Organização do Estado | tema | dc | 57 | B | 19.39 | 288 | 1.00 | estavel | 0.87 | 5.5 | 10.4 | letra-lei | edital+prova |  |
| dc-con | Controle de Constitucionalidade | tema | dc | 55 | B | 18.58 | 275 | 1.00 | alta | 0.89 | 6.5 | 8.5 | jurisprudencia | edital+prova |  |
| dc-fund | Princípios Fundamentais | tema | dc | 21 | C | 3.92 | 58 | 1.00 | estavel | 0.64 | 1.5 | 14.0 | letra-lei | edital+prova |  |
| dc-dir-ind | Direitos individuais (art. 5º) | topico | dc-dir | 100 | A | 14.12 | 209 | 1.00 | estavel | 0.95 | 3.0 | 33.3 | letra-lei/jurisprudencia | edital+prova |  |
| dc-con-conc | Controle concentrado (ADI, ADC, ADPF) | topico | dc-con | 82 | A | 11.22 | 166 | 1.00 | alta | 0.92 | 4.0 | 20.5 | jurisprudencia | edital+prova |  |
| dc-org-adm | Administração pública (arts. 37–41) | topico | dc-org | 74 | A | 9.80 | 145 | 1.00 | estavel | 0.90 | 3.0 | 24.7 | letra-lei | edital+prova |  |
| dc-pod-jud | Poder Judiciário | topico | dc-pod | 63 | A | 8.38 | 124 | 1.00 | estavel | 0.88 | 2.5 | 25.2 | letra-lei | edital+prova |  |
| dc-pod-leg | Poder Legislativo | topico | dc-pod | 55 | B | 6.89 | 102 | 1.00 | estavel | 0.86 | 2.5 | 22.0 | letra-lei | edital+prova |  |
| dc-dir-rem | Remédios constitucionais | topico | dc-dir | 51 | B | 6.42 | 95 | 1.00 | estavel | 0.85 | 2.0 | 25.5 | letra-lei/jurisprudencia | edital+prova |  |
| dc-pod-exe | Poder Executivo | topico | dc-pod | 46 | B | 5.61 | 83 | 1.00 | estavel | 0.84 | 2.0 | 23.0 | letra-lei | edital+prova |  |
| dc-dir-pol | Direitos políticos e partidos | topico | dc-dir | 44 | B | 5.41 | 80 | 1.00 | estavel | 0.83 | 1.5 | 29.3 | letra-lei | edital+prova |  |
| dc-org-comp | Repartição de competências | topico | dc-org | 43 | B | 5.14 | 76 | 1.00 | queda | 0.82 | 1.5 | 28.7 | letra-lei | edital+prova |  |
| dc-dir-soc | Direitos sociais | topico | dc-dir | 40 | C | 4.80 | 71 | 1.00 | alta | 0.78 | 1.5 | 26.7 | letra-lei | edital+prova |  |
| dc-org-ent | Entes federativos e federação | topico | dc-org | 38 | C | 4.53 | 67 | 1.00 | estavel | 0.76 | 1.0 | 38.0 | letra-lei | edital+prova |  |
| dc-con-dif | Controle difuso | topico | dc-con | 36 | C | 4.19 | 62 | 1.00 | estavel | 0.80 | 1.5 | 24.0 | jurisprudencia | edital+prova |  |
| dc-pod-fun | Funções essenciais à Justiça | topico | dc-pod | 30 | C | 3.38 | 50 | 1.00 | estavel | 0.74 | 1.5 | 20.0 | letra-lei | edital+prova |  |
| dc-con-sum | Súmula vinculante e repercussão geral | topico | dc-con | 29 | C | 3.18 | 47 | 1.00 | alta | 0.73 | 1.0 | 29.0 | jurisprudencia | edital+prova |  |
| dc-dir-nac | Nacionalidade | topico | dc-dir | 27 | C | 3.11 | 46 | 1.00 | estavel | 0.72 | 1.0 | 27.0 | letra-lei | edital+prova |  |
| dc-fund-obj | Objetivos e fundamentos da República | topico | dc-fund | 25 | C | 2.77 | 41 | 1.00 | estavel | 0.70 | 1.0 | 25.0 | letra-lei | edital+prova |  |
| dc-fund-rel | Relações internacionais | topico | dc-fund | 12 | D | 1.08 | 16 | 0.60 | queda | 0.28 | 0.5 | 24.0 | letra-lei | edital | promover_se_confirmado |

## 4. Arestas

`contem` (22) é a hierarquia — omitida aqui, está implícita na coluna `pai`.

| de | para | tipo | força | evidência |
|---|---|---|---|---|
| dc-con-conc | dc-con-sum | prerequisito | 1.00 | súmula vinculante pressupõe o controle |
| dc-con-dif | dc-con-conc | prerequisito | 0.90 | difuso antes de concentrado |
| dc-dir-ind | dc-con-conc | prerequisito | 0.80 | direitos são o parâmetro de controle |
| dc-dir-ind | dc-dir-nac | prerequisito | 0.70 | titularidade depende do art. 5º |
| dc-dir-ind | dc-dir-rem | prerequisito | 1.00 | remédios protegem os direitos do art. 5º |
| dc-dir-ind | dc-dir-soc | prerequisito | 0.60 | eficácia dos direitos antes dos sociais |
| dc-dir-pol | dc-pod-leg | prerequisito | 0.70 | mandato e representação |
| dc-fund-obj | dc-dir-ind | prerequisito | 0.90 | princípios fundam os direitos |
| dc-fund-obj | dc-org-ent | prerequisito | 0.80 | forma de Estado nasce nos princípios |
| dc-org-ent | dc-org-adm | prerequisito | 0.70 | competência antes da máquina |
| dc-org-ent | dc-org-comp | prerequisito | 1.00 | federação antes da repartição |
| dc-org-ent | dc-pod-leg | prerequisito | 0.60 | bicameralismo e federação |
| dc-pod-jud | dc-con-dif | prerequisito | 0.90 | difuso é exercido pelo Judiciário |
| dc-con-conc | dc-con-dif | coocorre | 0.35 | 22 questões cobram os dois |
| dc-dir-ind | dc-dir-rem | coocorre | 0.42 | 40 questões cobram os dois |
| dc-org-adm | dc-pod-exe | coocorre | 0.28 | 18 questões cobram os dois |
| dc-org-comp | dc-org-ent | coocorre | 0.31 | 19 questões cobram os dois |
| dc-org-adm | dc-dir-pol | correlato | 0.25 | agentes públicos e direitos políticos |

## 6. Lacunas e ressalvas

- **prova de 2026 ainda não catalogada** — a janela cobre 2021–2025 de fato.
- **fixture** — números sintéticos; nenhuma fonte real por trás.

1 nó com confiança abaixo de 0.30: dc-fund-rel. O peso dele é hipótese, não medição.
