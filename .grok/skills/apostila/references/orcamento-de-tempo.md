# Dimensionar a aula

A faixa é rígida: **20 a 45 minutos de conteúdo**. Abaixo de 20 a aula não justifica a sessão
de estudo; acima de 45 a atenção cai e a revisão fica pesada demais para caber numa rotina.

O tempo é restrição de projeto e **nunca aparece no documento impresso**.

## Quando o plano de estudo decide

Havendo `plano.json` da skill `montar-sumario`, a duração já vem calculada a partir do custo
do tópico no grafo de incidência, e já respeita a faixa:

```bash
python3 .grok/skills/apostila/scripts/contexto_aula.py sumarios/<slug>/plano.json --seq 3
```

Um tópico grande já chega fatiado (`minutos_por_aula: [30, 30]`); pegue a fatia com `--parte`.
Não recalcule: a grade equilibra o curso inteiro, e uma aula que estoura desloca as seguintes.

## Quando você decide

Sem plano, conte as **unidades de conteúdo** do tema. Uma unidade é cada:

- conceito que precisa ser definido antes de ser usado;
- dispositivo legal cobrado (artigo, inciso, súmula);
- classificação ou rol que o estudante precisa dominar;
- exceção relevante à regra;
- pegadinha recorrente de banca.

Cada unidade custa de **450 a 550 palavras**, porque ensinar de verdade exige situação
concreta, regra, razão da regra, exemplo e erro típico (`references/didatica.md`). Enunciar a
regra em duas linhas sai por 80 palavras — e não ensina ninguém.

| unidades | duração-alvo |
|---|---|
| até 4 | 20–25 min |
| 5 a 7 | 26–34 min |
| 8 a 11 | 35–45 min |
| mais de 11 | **divida em duas ou mais aulas**, cada uma dentro da faixa |

A conta é deliberadamente conservadora. **Cobrir menos e ensinar bem vence cobrir tudo e
ensinar mal** — o assunto que sobrou vira a próxima aula, e nada se perde.

Anuncie a decisão em uma linha antes de escrever — "tema com 13 unidades → aula de ~38 min" —
e siga. Se o usuário pedir outra duração, a dele prevalece.

**Com material fornecido**, dimensione pelo volume real aproveitável (palavras ÷ 170), não pela
contagem teórica.

**Tema pequeno demais** não vira apostila magra: aprofunde com exemplos, jurisprudência e casos
de prova até alcançar o piso, ou funda com o tópico seguinte.

**O teto de 45 min é rígido.** Estourar significa dividir a aula — nunca comprimir o conteúdo
nem cortar as caixas de sinalização para caber.

## O modelo de tempo

```
minutos = palavras/170
        + 0,3 × caixas
        + 0,8 × tabelas
        + 0,5 × (pare-e-responda + checkpoints)
        + 0,3 × passo-a-passo
        + 0,2 × exemplos
        + 0,8 × quadro-síntese
```

170 palavras/min é leitura de **estudo** em português — texto denso, com anotação e releitura —
e não leitura corrida (que fica perto de 250). Os acréscimos cobrem a parada que cada elemento
provoca: é para isso que eles existem.

## Orçamento de palavras

| alvo | palavras de corpo | unidades que cabem |
|---|---|---|
| 20 min | ~2.000 | 4 |
| 25 min | ~2.900 | 5 |
| 30 min | ~3.700 | 7 |
| 35 min | ~4.600 | 9 |
| 40 min | ~5.400 | 10 |
| 45 min | ~6.300 | 12 |

Já descontados ~8 min de caixas, exemplos, tabelas e checkpoints. Confira com:

```bash
python3 .grok/skills/apostila/scripts/estimar_tempo.py --alvo 30 --orcamento
python3 .grok/skills/apostila/scripts/estimar_tempo.py corpo.html --alvo 30
```

## O que fica fora da conta

Somam ao estudo, mas não à duração da aula:

| bloco | custo típico |
|---|---|
| 10 questões | ~13 min |
| gabarito comentado | ~4 min |
| primeira passada nos flashcards | ~3 min |

Ou seja: uma aula de 30 min ocupa cerca de 50 minutos de mesa. É deliberado — o usuário quis
o cronômetro medindo só o conteúdo, e é o conteúdo que você dimensiona.

## Ajustar quando estourar

`montar.py` sai com erro e diz quantas palavras faltam ou sobram. Na ordem, para cortar:

1. **Uma unidade de conteúdo inteira**, que passa para a próxima aula. É sempre o primeiro
   corte a considerar: preserva a profundidade do que fica.
2. Segundo exemplo do mesmo ponto — o primeiro já ancorou.
3. Contexto histórico e digressão que a prova não cobra.
4. Parágrafo de transição vazio ("como vimos, agora veremos").
5. Seção inteira — se o corte precisa ser grande, ela provavelmente é a segunda aula.

**Nunca corte para caber no tempo**: o exemplo que ancora o conceito, o parágrafo que explica
a razão da regra, o checkpoint, o quadro-síntese ou a caixa de pegadinha. Cortar isso devolve
o texto ao formato "resumo que não ensina", que é justamente o que esta skill não faz — corte
assunto, nunca didática.
