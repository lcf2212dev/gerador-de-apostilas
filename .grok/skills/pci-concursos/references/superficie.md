# Superfície do PCI Concursos

Conferido em 2026-08-17. Público, sem login.

## Listagem (HTTP)

- Índice: `https://www.pciconcursos.com.br/provas/`
- Cargo: `/provas/<slug-cargo>` (ex.: `/provas/oficial-de-justica`)
- Órgão: `/provas/trt-16`, `/provas/tj-es`
- Banca: `/provas/fgv`, `/provas/cebraspe`
- Página 2+: `/provas/<slug>/2`
- Tabela: Prova (link `/provas/download/<slug>`) · Ano · Órgão · Organizadora
- Rodapé: `Mostrando página N de M`

## Download (Playwright + Turnstile)

- `/provas/download/<slug>`
- Cloudflare Turnstile (`#captcha-provas`). Sem token, o clique é `preventDefault`.
- `a.prova-pdf-link` traz `data-code`, `data-arquivo`, `data-acao` (`ver`|`baixar`)
- POST `https://www.pciconcursos.com.br/provas/link` com `prova_code` +
  `cf-turnstile-response` → `{ok, arquivos:[{arquivo, ver, baixar}]}`
- Só então o `href` vira URL http. `pci.py baixar` espera esse href (até 90s).
- Headed (`PCI_HEADED=1`): complete o captcha na janela se não passar sozinho.
- Perfil Chrome: `~/.cache/concurso/pci-profile/` (não misturar com o QC)

## O que não é PDF

Página de erro ou HTML salvo com `.pdf` → descartar. `file` tem de dizer PDF.
