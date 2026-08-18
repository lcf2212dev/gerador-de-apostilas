# Apostila de concurso — via Claude

Pipeline: **mapa de incidência → sumário → aula → revisão**. O modelo escreve; o script
calcula e valida. Skills e agentes vivem em `.claude/`. Agentes com `model: inherit`
(o modelo da sessão, do início ao fim).

| fase | skill / agente | artefato |
|---|---|---|
| incidência | `mapear-conteudo` | `grafos/<slug>/` |
| ordem de estudo | `montar-sumario` | `sumarios/<slug>/` |
| uma aula | `apostila` + `gerador-aula` | `aulas/<disc>/aula-NN-*/` |
| double-check | `revisar-aula` + `revisor-aula` | fecha a pasta; só o PDF |
| curso inteiro | `curso-completo` | lotes de 16 geradores, depois 16 revisores |

QConcursos: se `.env` tiver `QCONCURSOS_*`, a skill `qconcursos` é a fonte primária
de incidência classificada. Sem login, web pública. Não imprima a senha.

PCI Concursos: skill `pci-concursos` baixa caderno e gabarito em PDF
(`.venv/bin/python .claude/skills/pci-concursos/scripts/pci.py`). Público, sem conta.

Cache/perfis de Chrome ficam em `~/.cache/concurso/`, fora do git.

Aula pronta = **só o PDF** na pasta da aula (depois da review). Não edite
`grafo.md` à mão.

Playwright e Chrome do sistema (`google-chrome-stable`) são dependências da máquina:
`uv venv .venv && uv pip install --python .venv/bin/python playwright && .venv/bin/playwright install chromium`.

## Duas vias no repositório

- `.grok/` é a via **legada** do Grok — não toque nela a partir do Claude; a via Claude
  é `.claude/` (nasceu como cópia em 2026-08-18 e evolui sozinha; ajustes não são
  retro-portados — antes de portar algo entre as vias, rode `diff -rq .grok .claude`).
- **Um curso, uma via**: as duas escrevem em `aulas/`, `grafos/` e `sumarios/`;
  nunca rode Grok e Claude sobre o mesmo assunto.
