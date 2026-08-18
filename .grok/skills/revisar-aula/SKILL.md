---
name: revisar-aula
description: >-
  Faz o double-check de UMA aula já gerada: fontes, HTML, PDF, didática, questões,
  vídeo aulas e normas. Se aprovar, fecha a pasta e deixa só o PDF. Use depois
  de /apostila ou quando curso-completo despacha o revisor-aula. Quem escreveu
  a aula não se auto-aprova.
---

# Revisar aula

Segunda passagem obrigatória. Aula pronta = **só o PDF** na pasta, depois desta
review. Enquanto houver fontes no disco, `progresso.py` trata como parcial.

Despacho traz `DIRETÓRIO`. Só mexa nele. Modelo: grok-4.6.

## Procedimento

1. Confira no disco: `meta.json`, `corpo.html`, `questoes.json`, `videos.json`,
   `flashcards.json`, `<slug>.html`, `<slug>.pdf`. PDF mais novo que o corpo.
2. Rode os validadores (caminhos literais):

```bash
python3 .grok/skills/apostila/scripts/estimar_tempo.py <DIR>/corpo.html --alvo 30
python3 .grok/skills/questoes-banca/scripts/validar_questoes.py <DIR>/questoes.json --corpo <DIR>/corpo.html
python3 .grok/skills/apostila/scripts/montar.py --dir <DIR>
```

3. Aplique a checklist. Bloqueio = não aprova até corrigir ou devolver.

| checagem | bloqueia |
|---|---|
| Cinco fontes + HTML + PDF; PDF ≥ corpo | sim |
| Tempo de conteúdo 25–40 min (script 20–45) | sim |
| Didática: seção sem exemplo, termo órfão, parágrafo-parede, juridiquês | sim se a revisão didática não sair limpa |
| 10 questões válidas; cada seção coberta; gabarito comentado | sim |
| QC: `origem=qconcursos` tem URL real; YouTube só AAA e passou em `yt.py inspecionar` | sim se YT < 85 ou link morto |
| Norma citada em vigor; `meta.json.fontes` com URL | sim se inventou artigo/súmula |
| Duração **não** aparece no documento | sim |
| 5 flashcards atômicos | aviso, salvo quantidade ≠ 5 |

4. **Ajuste pequeno** (fonte faltando, caixa a mais, card ambíguo, vídeo morto):
   corrija a fonte, remonte, regenere o PDF.
   **Buraco estrutural** (fora da faixa depois de 2 ajustes, assunto da vizinha,
   questões fora do corpo): `reprovada`, uma linha de motivo. Não reescreva a aula.

5. Se **aprovada**: remonte o PDF se ajustou algo e **feche** a pasta (só o PDF fica):

```bash
python3 .grok/skills/apostila/scripts/fechar_aula.py --dir <DIR>
```

Se **reprovada**: deixe as fontes no disco e devolva o motivo. Não rode `fechar_aula.py`.

6. Relatório no máximo 10 linhas. Sem data de geração no documento (o `montar.py`
já não imprime).

Aula isolada (`/apostila`): a sessão corre esta skill depois de montar. Sem
PDF isolado na pasta, não entregue como pronta.
