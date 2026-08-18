# Apostila de concurso

Pipeline: **mapa de incidência → sumário → aula → revisão**. O modelo escreve; o script
calcula e valida. Skills e agentes vivem em `.grok/`. Modelo: **grok-4.6**.

| fase | skill / agente | artefato |
|---|---|---|
| incidência | `mapear-conteudo` | `grafos/<slug>/` |
| ordem de estudo | `montar-sumario` | `sumarios/<slug>/` |
| uma aula | `apostila` + `gerador-aula` | `aulas/<disc>/aula-NN-*/` |
| double-check | `revisar-aula` + `revisor-aula` | fecha a pasta; só o PDF |
| curso inteiro | `curso-completo` | lotes de 3 geradores, depois 3 revisores |

QConcursos: se `.env` tiver `QCONCURSOS_*`, a skill `qconcursos` é a fonte primária
de incidência classificada. Sem login, web pública. Não imprima a senha.

PCI Concursos: skill `pci-concursos` baixa caderno e gabarito em PDF
(`.venv/bin/python .grok/skills/pci-concursos/scripts/pci.py`). Público, sem conta.

Cache/perfis de Chrome ficam em `~/.cache/concurso/`, fora do git.

Aula pronta = **só o PDF** na pasta da aula (depois da review). Não edite
`grafo.md` à mão.

Playwright e Chrome do sistema (`google-chrome-stable`) são dependências da máquina:
`uv venv .venv && uv pip install --python .venv/bin/python playwright && .venv/bin/playwright install chromium`.
