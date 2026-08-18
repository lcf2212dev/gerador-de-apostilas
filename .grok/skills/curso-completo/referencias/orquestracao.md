# Orquestração da produção — despacho, lotes, falhas, retomada

## Prompts

Valores vêm do `progresso.py --pendentes --json`. Use `spawn_subagent` com
`subagent_type: gerador-aula` ou `revisor-aula`. `cwd` na raiz do repo. grok-4.6.

**Gerador:**

```
SUMÁRIO: sumarios/<slug>
AULA: seq <N>
DIRETÓRIO: <dir exato devolvido pelo progresso.py>
DURAÇÃO ALVO: 30 min (faixa aceita 25–40)

Gere essa aula de ponta a ponta pela sua skill. Não pergunte nada ao usuário.
Se o diretório já tiver arquivos válidos, reaproveite em vez de refazer.
Se houver revisao.json reprovada, corrija só o que ela aponta.
Devolva o relatório no formato padrão.
```

**Revisor** (depois que o gerador daquele diretório voltou):

```
DIRETÓRIO: <mesmo dir>
SUMÁRIO: sumarios/<slug>
AULA: seq <N>

Revise essa aula pela skill revisar-aula. Se aprovar, feche a pasta (só o PDF).
Não reescreva do zero.
```

O briefing completo o subagente extrai com `contexto_aula.py` — não duplique no prompt.

## Política de lotes

- **3 geradores por vez**, depois **3 revisores** nos mesmos diretórios. Diretórios
  disjuntos; o teto de 3 protege YouTube/QC de rate limit.
- O revisor **não** é filho do gerador (Grok não aninha).
- Lote novo só depois de geradores **e** revisores voltarem **e** de `progresso.py`
  confirmar no disco.
- Entre lotes, imprima uma linha por aula do lote: `seq · status · tempo · avisos` — e o
  rodapé do progresso (prontas/pendentes/cobertura). É o que deixa o usuário acompanhar um
  curso de dezenas de aulas sem rolar tela.

## Falhas

- Uma FALHA no lote não interrompe as outras duas nem o laço. Registre `seq · FALHA ·
  motivo` e siga.
- Terminado o laço principal, **um** único passe de reprocessamento: despache de novo só as
  falhas (o que o subagente deixou no disco vira retomada — ele reaproveita). Falhou de
  novo: fica pendente, aparece no fechamento, e a próxima invocação da skill tenta de novo.
- Falha repetida com o mesmo motivo em aulas diferentes (ex.: Chrome ausente, script
  quebrado) é problema de máquina, não de aula: **pare o laço** e reporte ao usuário em vez
  de queimar subagente em série.

## Retomada

- Reinvocada a skill, a fase 0 roda `progresso.py` e o laço da fase 4 continua dos
  pendentes/parciais — sem refazer grafo, sumário nem aula pronta.
- `parcial` se despacha igual a `pendente`: o subagente vê o diretório, reaproveita o que
  está válido e completa o que falta (é por isso que o despacho manda "reaproveite").
- `CONFLITO` nunca entra no lote. Diretório `aula-NN-*` com slug diferente do esperado
  significa sumário regenerado com outros títulos ou aula feita fora do sumário — decisão
  humana: renomear, apagar ou ignorar. Reporte e pergunte **uma vez**, no fim do laço, não
  no meio.
