---
name: qconcursos
description: >-
  Acessa a conta QConcursos do .env via Playwright e baixa o que a assinatura
  libera: questões com gabarito, videoaulas, editais/provas e Raio X. Use quando
  o usuário pedir para logar no QC, baixar questões, raio x, aulas do QC, ou
  quando mapear-conteudo / questoes-banca / videos-aula precisarem da plataforma.
  Sem .env ou login falho, as outras skills caem para a web pública.
---

# QConcursos

Dona do site. Nenhuma outra skill loga no QC nem inventa seletor — chama este
cliente. Rode sempre pelo venv do projeto (Playwright vive lá):

```bash
.venv/bin/python .claude/skills/qconcursos/scripts/qc.py status
.venv/bin/python .claude/skills/qconcursos/scripts/qc.py login
```

Credenciais: `QCONCURSOS_LOGIN`, `QCONCURSOS_PASSWORD`, `QCONCURSOS_URL` no `.env`.
Nunca imprima a senha. Cache em `~/.cache/concurso/qconcursos/`; perfil Chrome em
`~/.cache/concurso/qc-profile/`.

## Ordem

1. `status`. Exit 0 e `logado: true` → siga. Sem `.env` → pare e use a web pública.
2. Se `logado: false`, `login` (headed, QC_HEADED=1). Cloudflare no headless é esperado.
3. Comando do recorte pedido. Coleta grande: `--max` + retomada; o cache é idempotente.
4. Falha de challenge ou paywall: exit ≠ 0, registre lacuna, não invente número.

## Comandos

| comando | o que devolve |
|---|---|
| `status` / `login` | se a sessão existe; plano detectado |
| `raiox --banca --disciplina --de --ate` | assuntos com n e % |
| `questoes --disciplina --assunto --banca --ano --max N` | itens da listagem (enunciado, alts, meta) |
| `questao <id>` | página completa + aulas relacionadas |
| `aulas --disciplina --assunto --max N` | videoaulas/playlists com URL canônica |
| `editais --orgao --ano` | provas/editais listados |
| `prova --id SLUG` | baixa PDF se a UI oferecer |

URLs e seletores: `references/superficie.md`. Site muda → o script falha alto; atualize
a superfície, não finja extração.

## O que vale como evidência

- Questões e Raio X alimentam `mapear-conteudo` (`tipo: plataforma` ou itens com `fonte`).
- Itens reais calibram `questoes-banca`; a apostila **imprime 10 itens originais**, não o
  enunciado do QC. Cite o id/URL na `fonte` se o item foi calibrado nele.
- Videoaulas entram em `videos.json` com `origem: "qconcursos"` (link, sem score AAA).
- Só o que a conta abre. Plano bloqueado = lacuna, não contorno.

## Ritmo

Um recorte por vez. `QC_QPS` (padrão 0,4) limita a cadência. Login headed; coletas
seguintes reusam o perfil. Se o challenge voltar, `login` de novo.
