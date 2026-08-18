---
name: pci-concursos
description: >-
  Busca e baixa provas e gabaritos em PDF no PCI Concursos
  (pciconcursos.com.br/provas). Use quando o usuário pedir prova, gabarito,
  caderno de questões, download de prova de concurso, ou quando mapear-conteudo
  precisar de PDFs públicos. Não classifica questão por assunto — isso é
  qconcursos. Sem login.
---

# PCI Concursos

Dona de `https://www.pciconcursos.com.br/provas/`. Caderno oficial + gabarito
em PDF. A tabela lista; o arquivo está um pulo depois (`/provas/download/<slug>`),
com verificação de segurança e clique JS.

```bash
.venv/bin/python .grok/skills/pci-concursos/scripts/pci.py buscar \
    --cargo "Oficial de Justiça" --banca FGV --ano 2022 --max 20
.venv/bin/python .grok/skills/pci-concursos/scripts/pci.py baixar <slug> \
    --para grafos/<assunto>/fontes/
```

## Comandos

| comando | o que faz |
|---|---|
| `buscar --cargo/--orgao/--banca/--ano/--max` | lê a tabela (HTTP). Slug, título, ano, órgão, banca |
| `pagina --cargo X` | uma URL só, sem paginar o resto |
| `baixar <slug> [--para DIR]` | Playwright: prova e gabarito se existirem; `file`/`sha256`; `pdftotext -layout` |

Cache em `~/.cache/concurso/pci/`. Destino do grafo: `grafos/<slug>/fontes/`.
Idempotente: PDF já válido não baixa de novo.

O `baixar` abre o Chrome headed e espera o Turnstile liberar os `href`. Se a
verificação não passar sozinha, complete o captcha na janela. Sem token o site
engole o clique (`javascript:void(0)`).

HTML no lugar de PDF → `status: falha`, sem inventar conteúdo. Questão anulada
no gabarito definitivo não entra em `questoes[]`.

Seletores e o pulo do download: `references/superficie.md`.
