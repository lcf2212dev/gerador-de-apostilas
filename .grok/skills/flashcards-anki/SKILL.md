---
name: flashcards-anki
description: Cria flashcards de revisão espaçada a partir de um conteúdo de estudo e os insere automaticamente no Anki (via AnkiConnect, com .tsv e .apkg como alternativa). Use quando o usuário pedir flashcards, cards, cartões de memorização, revisão espaçada ou importação para o Anki. Também usada pela skill apostila para gerar os 5 cards de cada aula.
---

# Flashcards para o Anki

Escreve **5 flashcards** por aula (ou a quantidade pedida fora do contexto de apostila) e os
manda direto para a coleção do Anki. Cinco cards bons valem mais que vinte medíocres: cada
card é uma dívida diária de revisão pelos próximos meses, então só entra o que realmente
precisa ser memorizado.

## Fluxo

1. **Escolher o que vira card.** Leia `references/principios-flashcards.md` antes de escrever.
   Selecione o que passa neste filtro: é fato ou distinção que o estudante precisa recuperar
   de memória na prova, e que ele erraria hoje. O resto fica na apostila.
2. **Escrever os cards** — atômicos, uma informação por card, sem ambiguidade sobre o que se
   espera como resposta.
3. **Gravar `flashcards.json`** no diretório da aula (contrato abaixo).
4. **Importar:**
   ```
   python3 .grok/skills/flashcards-anki/scripts/anki_import.py aulas/<disciplina>/aula-NN-<slug>
   ```
   Com o Anki aberto, os cards entram na hora. Fechado, o script gera `flashcards.tsv` com
   deck e tags embutidos, pronto para *Arquivo > Importar*. `--apkg` produz também um pacote.
5. **Relatar** quantos entraram e em qual deck.

O script é idempotente: rodar de novo não duplica nada, apenas informa o que já existia. Isso
permite corrigir um card, rodar outra vez e ter só a diferença aplicada.

## Contrato — `flashcards.json`

```json
{
  "deck": "Concurso::Direito Constitucional::Aula 03 — Princípios Fundamentais",
  "tags": ["concurso", "direito-constitucional", "aula-03"],
  "cards": [
    {
      "tipo": "basico",
      "frente": "Qual inciso do art. 1º da CF/88 traz a dignidade da pessoa humana?",
      "verso": "Inciso III.",
      "extra": "CF/88, art. 1º, III",
      "origem_secao": "1"
    },
    {
      "tipo": "cloze",
      "texto": "São Poderes da União, {{c1::independentes e harmônicos}} entre si.",
      "extra": "CF/88, art. 2º",
      "origem_secao": "2"
    }
  ]
}
```

- `deck` hierárquico com `::` — `Concurso::<Disciplina>::Aula NN — <Título>`. A hierarquia
  deixa o usuário estudar a aula isolada ou a disciplina inteira.
- `tipo`: `basico` (usa `frente` + `verso`) ou `cloze` (usa `texto` com `{{c1::…}}`).
  Vários `c1`, `c2` no mesmo texto geram vários cards no Anki — use com parcimônia.
- `extra`: o fundamento (artigo, súmula, página). Aparece discreto abaixo da resposta e é o
  que permite conferir depois.
- `origem_secao`: seção da aula de onde o card saiu.
- HTML inline simples é permitido nos campos (`<b>`, `<i>`, `<br>`).

## Como o script decide o modelo de nota

A coleção pode estar em qualquer idioma. O script lê os modelos existentes e reconhece o
básico e o de omissão em português ou inglês ("Básico"/"Basic", "Omissão de Palavras"/"Cloze"),
mapeando os campos por posição. Não crie modelos novos.

## Erros que anulam o benefício

- Card que pede uma lista inteira de cor ("cite os cinco fundamentos") — vira um card que se
  erra para sempre. Quebre em cinco, ou use um mnemônico como resposta única.
- Frente ambígua: "Art. 5º" não diz o que responder.
- Copiar um parágrafo inteiro no verso. Se a resposta não cabe em uma linha ou duas, o card
  está errado.
- Card que só faz sentido para quem lembra da aula ("o que vimos na seção 2?").
