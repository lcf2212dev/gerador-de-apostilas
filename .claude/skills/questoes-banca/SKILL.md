---
name: questoes-banca
description: Cria 10 questões de múltipla escolha em estilo de banca de concurso, com gabarito comentado alternativa por alternativa, a partir do conteúdo de uma aula ou de um material de estudo. Use quando o usuário pedir questões, simulado, exercícios de fixação, itens de prova ou o bloco de questões de uma apostila. Também usada pela skill apostila para gerar questoes.json.
---

# Questões em estilo de banca

Gera **exatamente 10 questões** sobre um conteúdo, no formato `questoes.json`, e valida o
resultado com um script antes de entregar. O objetivo não é decorar o texto da aula: é medir
se o estudante consegue resolver um item real de prova.

## Fluxo

1. **Levantar o conteúdo.** Se estiver montando uma apostila, leia o `corpo.html` da aula e
   liste as seções (`<h2>`). Fora desse contexto, peça ou leia o material de origem.
   Se `qc.py status` estiver logado, puxe um recorte do tema/banca (`qc.py questoes` /
   `questao`) para calibrar o dialeto — a apostila continua com **10 itens originais**.
2. **Definir o estilo.** Padrão `A-E` (FGV, FCC, VUNESP, Cesgranrio). Outros aceitos: `A-D`
   (IBFC, AOCP, bancas municipais) e `cebraspe-ce` (itens Certo/Errado). O estilo vem de
   `meta.json` quando existir. Leia `references/estilos-banca.md` para o dialeto da banca.
3. **Planejar a matriz** antes de escrever, cobrindo:
   - **cobertura**: toda seção da aula precisa de pelo menos uma questão;
   - **dificuldade**: 3 fáceis, 5 médias, 2 difíceis;
   - **competência**: no mínimo 4 itens acima de "lembrar" (compreender, aplicar, analisar).
4. **Escrever os itens** seguindo `references/rubrica-item.md` — essa leitura não é opcional,
   é ela que separa um item de banca de um quiz.
5. **Comentar o gabarito**: por que a correta está correta (com o dispositivo ou o trecho que
   a fundamenta) e por que **cada** distrator falha. O comentário do erro precisa ensinar algo,
   não apenas dizer "está incorreto".
6. **Validar**:
   ```
   python3 .claude/skills/questoes-banca/scripts/validar_questoes.py questoes.json --corpo corpo.html
   ```
   Erros são bloqueantes: corrija e rode de novo até sair limpo. Avisos exigem julgamento —
   ou corrija, ou explique ao usuário por que aquele caso se justifica.

## Contrato — `questoes.json`

```json
{
  "banca_estilo": "A-E",
  "questoes": [
    {
      "id": 1,
      "secao": "2",
      "nivel": "media",
      "competencia": "aplicar",
      "enunciado": "Texto do item, sem pistas gramaticais para a resposta.",
      "alternativas": {
        "A": "...", "B": "...", "C": "...", "D": "...", "E": "..."
      },
      "gabarito": "C",
      "justificativa": "Por que C está correta, com o fundamento.",
      "erros": {
        "A": "o que o candidato confundiu ao marcar A",
        "B": "...", "D": "...", "E": "..."
      },
      "fonte": "CF/88, art. 5º, LXIII"
    }
  ]
}
```

- `nivel`: `facil` | `media` | `dificil` · `competencia`: `lembrar` | `compreender` | `aplicar` | `analisar`
- `secao`: número da seção da aula que o item cobra (para o gabarito remeter ao conteúdo).
- No estilo `cebraspe-ce`: omita `alternativas`, use `gabarito` igual a `"C"` ou `"E"` e
  escreva `justificativa` explicando o julgamento; `erros` pode trazer a chave `"C"` ou `"E"`
  com a leitura equivocada que induziria ao erro.
- Nas strings valem apenas as tags inline `<strong> <b> <em> <i> <sup> <sub> <code> <abbr> <small> <br>`.
  Qualquer outro `<` é escapado automaticamente.

## Regras inegociáveis

- **Dez itens.** Nem nove, nem onze.
- **Uma única resposta defensável.** Se dois distratores podem ser sustentados, o item está quebrado.
- **Nada de "todas as anteriores", "nenhuma das anteriores" ou "n.d.a."**
- **Gabarito distribuído**: cada letra aparece ao menos uma vez, nenhuma domina o conjunto,
  e nunca três iguais em sequência.
- **A correta não pode ser a mais longa** de forma sistemática — é a pista que mais entrega
  resposta em prova. O validador mede isso.
- **Fundamento verificável**: `fonte` sempre preenchido. Em matéria de lei, cite o dispositivo;
  se a lei mudou depois do que você sabe, confirme antes de afirmar. Se o item foi calibrado
  numa questão real do QC, acrescente o id/URL — sem colar o enunciado deles no PDF.
- Não invente jurisprudência, número de súmula ou de artigo. Na dúvida, verifique ou reformule
  o item para não depender do número.
- Não copie enunciado do QConcursos. Use o banco para ver como a banca pergunta.
