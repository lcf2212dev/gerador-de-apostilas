# Apostila de concurso

Gera material de estudo a partir do que **cai de verdade**: mapa de incidência →
sumário → aulas em PDF (25–40 min), com 10 questões estilo banca, vídeos e
flashcards. Cada aula passa por um segundo agente antes de contar como pronta.

Fale com o Grok na raiz deste repositório. As skills estão em `.grok/skills/`.

## Uma vez na máquina

```bash
uv venv .venv
uv pip install --python .venv/bin/python playwright
.venv/bin/playwright install chromium
```

Chrome do sistema (`google-chrome-stable`) gera o PDF da apostila e abre o
QConcursos / PCI.

Conta QConcursos (opcional, mas é a melhor fonte de incidência):

```bash
# .env — não commitar (já está no .gitignore)
QCONCURSOS_LOGIN="voce@email.com"
QCONCURSOS_PASSWORD="…"
QCONCURSOS_URL="https://www.qconcursos.com"
```

```bash
.venv/bin/python .grok/skills/qconcursos/scripts/qc.py login
.venv/bin/python .grok/skills/qconcursos/scripts/qc.py status
```

Sem `.env`, o pipeline usa a web pública (PCI, editais, YouTube).

## Curso inteiro

O atalho. Encadeia mapa → sumário → todas as aulas → review.

```
/curso-completo Português para concursos bancários
(Banco do Nordeste, Caixa Econômica Federal e Banco do Brasil).
Tipo: disciplina. Órgãos-alvo: BNB, CEF, BB.
Janela: últimos 5 anos. Perfil: profundo.
Banca-alvo: Cesgranrio.
```

Outros exemplos:

```
/curso-completo Direito Constitucional para Analista Judiciário, banca FGV, 2021–2026
```

```
/curso-completo continua o Português bancário
```

A segunda invocação **retoma o disco**: não refaz grafo nem aula já aprovada.
Pode interromper no meio.

Cada lote escreve 3 aulas e depois 3 reviews. Uma aula só fica pronta com PDF
**e** `revisao.json` com `"status": "aprovada"`.

## Por etapas

Útil para conferir o mapa antes de gastar produção.

**1. O que cai**

```
/mapear-conteudo Português, órgãos BNB, CEF e BB, banca Cesgranrio, últimos 5 anos
```

Saída: `grafos/<slug>/` — leia `relatorio.md` (confiança, top 15, lacunas).

**2. Em que ordem estudar**

```
/montar-sumario a partir de grafos/<slug>
```

Saída: `sumarios/<slug>/` — `sumario.md`, `plano.json`, `grade.json`, `lacunas.md`.

**3. Uma aula só** (para ver o padrão)

```
/apostila gera a aula 1 do sumário de português-bancarios
```

Depois o próprio fluxo chama `/revisar-aula`. Sem review aprovado, não entregue
como pronta.

**4. O resto**

```
/curso-completo escreve as aulas que faltam no sumário de português-bancarios
```

## O que aparece no disco

```
grafos/<slug>/
  grafo.md            # derivado — não edite
  evidencias.json     # fonte da verdade
  relatorio.md

sumarios/<slug>/
  sumario.md
  plano.json
  grade.json          # uma linha por aula
  lacunas.md

aulas/<disciplina>/aula-01-<tema>/
  <slug>.pdf              # aula fechada: só o PDF
  # durante a produção ainda existem as fontes (meta, corpo, json, html)
```

Acompanhar produção:

```bash
python3 .grok/skills/curso-completo/scripts/progresso.py sumarios/<slug>
python3 .grok/skills/curso-completo/scripts/progresso.py sumarios/<slug> --pendentes --limite 3
```

## Fontes, na mão

### QConcursos (questões classificadas, Raio X, aulas da plataforma)

```
/qconcursos baixa o Raio X de Português, banca Cesgranrio, 2021–2026
```

```bash
.venv/bin/python .grok/skills/qconcursos/scripts/qc.py raiox \
    --disciplina "Língua Portuguesa" --banca Cesgranrio --de 2021 --ate 2026

.venv/bin/python .grok/skills/qconcursos/scripts/qc.py questoes \
    --disciplina "Língua Portuguesa" --banca Cesgranrio --max 40

.venv/bin/python .grok/skills/qconcursos/scripts/qc.py aulas \
    --disciplina "Língua Portuguesa" --assunto "crase" --max 5
```

Login headed (Cloudflare). Headless costuma cair. Senha nunca deve ir para o chat.

A apostila **não cola** enunciado do QC: gera 10 itens originais. Aulas do QC
entram como link; YouTube só no padrão AAA.

### PCI Concursos (caderno e gabarito em PDF)

```
/pci-concursos busca provas de Escriturário, banca Cesgranrio, 2024
```

```bash
.venv/bin/python .grok/skills/pci-concursos/scripts/pci.py buscar \
    --cargo "Escriturário" --banca Cesgranrio --ano 2024 --max 15

.venv/bin/python .grok/skills/pci-concursos/scripts/pci.py baixar <slug> \
    --para grafos/portugues-bancarios/fontes/
```

`buscar` é HTTP e imediato. `baixar` abre o Chrome e espera o Turnstile: se o
captcha não passar sozinho, complete na janela (`PCI_HEADED=1`).

## Flashcards (Anki)

No fim do curso, ou por aula, com o Anki aberto:

```bash
python3 .grok/skills/flashcards-anki/scripts/anki_import.py \
    aulas/<disciplina>/aula-01-<tema>
```

Sem Anki, o script gera `flashcards.tsv` para *Arquivo → Importar*. Rodar de
novo não duplica.

## Skills (atalhos)

| comando | quando usar |
|---|---|
| `/curso-completo` | apostila inteira, do zero ou retomada |
| `/mapear-conteudo` | só o grafo de incidência |
| `/montar-sumario` | só a ordem de estudo |
| `/apostila` | uma aula |
| `/revisar-aula` | double-check de uma aula já gerada |
| `/qconcursos` | conta QC: questões, Raio X, videoaulas |
| `/pci-concursos` | PDF de prova e gabarito |
| `/questoes-banca` | 10 itens estilo banca, sem montar a aula |
| `/videos-aula` | QC + YouTube AAA |
| `/flashcards-anki` | 5 cards e import |

## Regras que evitam dor

- Não edite `grafo.md` nem o HTML gerado — o próximo build/montagem apaga.
- Número sem URL acessada não entra no grafo.
- Confiança global abaixo de 0,40 no `relatorio.md`: o mapa orienta, não decide.
- Cache e perfil do Chrome ficam em `~/.cache/concurso/`, fora do git.
- `.env` não se commita.
