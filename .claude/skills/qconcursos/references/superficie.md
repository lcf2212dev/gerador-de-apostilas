# Superfície do QConcursos

Conferido em 2026-08-17 com a conta do `.env` (plano Ilimitado Básico), Chrome
headed + perfil persistente. Headless cai no Cloudflare (`Just a moment`).

## Login

- URL: `https://www.qconcursos.com/conta/entrar`
- `#login_email` (`user[email]`), `#login_password` (`user[password]`), `#btnLogin`
- Sucesso: `https://www.qconcursos.com/usuario`, texto com "Meu Painel" / "ASSINATURA …"
- Cloudflare no título `Just a moment...` — esperar ou falhar; não parsear o interstício

## Questões

- Lista: `/questoes-de-concursos/questoes` (20 por página, `?page=N`)
- Por disciplina: `/questoes-de-concursos/disciplinas/<slug>/questoes`
  - Direito Constitucional → `direito-direito-constitucional`
  - Português → `letras-portugues`
- Card: `.js-question-item` > `.js-question[data-question-id]`
- Link canônico: `/questoes-de-concursos/questoes/<uuid>`
- Código visível `Q4237344`; meta no texto: `Ano:`, `Banca:`, `Órgão:`, `Prova:`
- Gabarito: botão "Gabarito Comentado" na página do item

## Aulas

- Catálogo: `/questoes-de-concursos/aulas` (busca rápida no campo da página)
- `/questoes-de-concursos/disciplinas/<slug>/aulas` e `/aulas` devolvem **404**
- Playlists: `/playlist/<slug>` — filtrar pelo título/slug do assunto; a home mistura
  carreiras (BB, INSS, PRF) na lateral
- Relacionadas a uma questão: bloco "Aulas (N)" no card / página do item

## Raio X

- Marketing: `/raiox`
- Ferramenta logada: `/usuario/ferramentas/raio-x`
- Análises existentes: `/usuario/ferramentas/raio-x/<n>` e `?page=`

## Provas / editais

- `/questoes-de-concursos/provas`
- Busca do header: `#search-header`

## Chrome

Canal `chrome` (`/usr/bin/google-chrome-stable`). Perfil:
`~/.cache/concurso/qc-profile/`. Init script mascara `navigator.webdriver`.
`locale=pt-BR`, `timezone=America/Sao_Paulo`.
