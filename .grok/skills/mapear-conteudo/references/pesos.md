# Metodologia dos pesos

Tudo aqui é implementado em `scripts/grafo.py`. Este documento existe para que o resultado
seja **auditável**: qualquer número do `grafo.md` pode ser refeito à mão a partir de
`evidencias.json` seguindo estas fórmulas.

O problema que os pesos resolvem: um edital lista "Controle de Constitucionalidade" e "Ordem
Econômica" como dois itens iguais. Nas provas, um vale 12% e o outro 0,4%. Sem ponderação por
evidência, todo plano de estudos herda essa mentira.

---

## 1. Decaimento por recência

```
d(ano) = 0.5 ^ ((ano_ref − ano) / meia_vida)        meia_vida = 2.5 anos
```

`ano_ref` é sempre `janela.ate`, **nunca a data de execução** — é o que torna o build
determinístico e reproduzível meses depois.

| ano (ref. 2026) | 2026 | 2025 | 2024 | 2023 | 2022 | 2021 |
|---|---|---|---|---|---|---|
| `d` | 1.000 | 0.757 | 0.574 | 0.435 | 0.330 | 0.250 |

Por que meia-vida e não corte seco: legislação muda, jurisprudência assenta, banca troca de
estilo. Uma prova de 2021 ainda informa, mas informa menos — e a transição precisa ser suave,
senão o grafo muda bruscamente quando a janela avança um ano.

## 2. Peso da banca

```
b(banca) = 1.00  se a banca é alvo
b(banca) = 0.45  caso contrário
b(banca) = 1.00  para todas, se banca_alvo estiver vazio
```

Prova de outra banca prevê pior, mas prevê. Zerar seria jogar fora informação real;
não descontar seria fingir que Cebraspe e FGV cobram igual.

## 3. Incidência

```
I_dir(n) = Σ_questões  (peso_q / k_q) · d(ano_fonte) · b(banca_fonte)
```

`k_q` é o número de nós que a questão cobre. Uma questão que mistura dois assuntos entrega
meia questão a cada um — contar inteira nos dois inflaria o total além do número de questões
que realmente existem.

Agregação bottom-up pela hierarquia:

```
I_sub(n) = I_dir(n) + Σ_filhos I_sub(filho)
```

Fontes com `status: falha` e fontes fora da janela não entram. Nada é estimado no lugar delas.

## 4. Cobertura editalícia

```
              Σ_editais  m(n,e) · d(ano_e) · b(banca_e)
E(n) = ────────────────────────────────────────────────       m: explícita 1.0, genérica 0.5
              Σ_editais  d(ano_e) · b(banca_e)
```

`E(n)` ∈ [0,1] lê-se como "fração ponderada dos editais que cobram este item". Propaga para
cima por `max`: se qualquer subtópico está no edital, o tema está.

Este componente é o que impede o grafo de ser míope. Um tópico recém-incluído no edital ainda
não caiu em prova nenhuma — a incidência é zero e a cobertura é 1,0.

## 5. Confiança

```
C(n) = 0.7 · n_q/(n_q + 5)  +  0.3 · (editais_que_cobrem / total_editais)
```

Satura: 5 questões → 0.35; 15 questões → 0.53; 50 questões → 0.64 (mais a parcela do edital).
Nunca chega a 1 — nenhuma amostra de provas passadas é certeza sobre a próxima prova.

Faixas: **< 0.30** frágil (o peso é hipótese) · **0.30–0.65** razoável · **> 0.65** sólida.

## 6. Encolhimento dentro do ramo

O ponto delicado. Um tópico que nunca caiu em 30 provas **não** é um tópico sem dados — é um
tópico observado zero vezes em muitas oportunidades. Uma média simples com os irmãos o
promoveria ao patamar dos vizinhos fortes; ignorar o encolhimento o mandaria a zero mesmo
quando a amostra foi pequena demais para concluir qualquer coisa.

Estimador Beta-binomial da fatia do nó dentro do ramo:

```
              I_sub(n)  +  m · (1/n_irmãos)
p̂(n) = ─────────────────────────────────────         m = 5 (questões equivalentes de prior)
              N_ramo  +  m

I_aj(n) = p̂(n) · N_ramo          (preserva a massa total do ramo)
```

Com `N_ramo` grande, o prior desaparece e vale a evidência. Com `N_ramo` pequeno, os irmãos
convergem para a média — que é exatamente a leitura correta de "a amostra não distingue".

## 7. Tendência

Compara as duas metades da janela usando **contagem crua**, sem decaimento — aplicar o
decaimento aqui seria contá-lo duas vezes, já que ele entra na incidência.

```
corte = (de + ate) / 2
s_rec = n_q_recente(n) / n_q_recente_total
s_ant = n_q_antigo(n)  / n_q_antigo_total
Δ = (s_rec − s_ant) / s_ant
```

| condição | tendência | multiplicador |
|---|---|---|
| Δ > +0.35 | `alta` | ×1.15 |
| Δ < −0.35 | `queda` | ×0.88 |
| entre os dois | `estavel` | ×1.00 |
| `n_q(n) < 4` ou uma das metades vazia | `indefinida` | ×1.00 |

O piso de 4 questões evita que ruído de amostra vire narrativa. A assimetria (+15% / −12%) é
deliberada: um assunto em ascensão costuma continuar subindo, mas um assunto "em queda" às
vezes só não caiu naquele ciclo — punir demais seria arriscado.

## 8. Peso final

```
bruto(n) = (0.65 · I_aj_norm(n)  +  0.35 · E(n)) · mult_tendência(n)

peso(n)  = 100 · bruto(n) / max(bruto no mesmo nível)
```

A normalização é **por nível**: o topo de cada nível vale 100. Comparar o peso de uma
disciplina com o de um tópico não significa nada — são escalas diferentes.

## 9. Classe (curva ABC)

Ordena por peso decrescente dentro do nível e acumula `share`. O corte olha o acumulado
**antes** do item: somar primeiro jogaria para a classe seguinte justamente o item grande que
cruza a fronteira.

| classe | acumulado antes do item | leitura |
|---|---|---|
| **A** | ≤ 50% | domina a prova; erra aqui e perde o concurso |
| **B** | ≤ 80% | importante; cobre o restante da massa |
| **C** | ≤ 95% | complementar; vale se sobrar tempo |
| **D** | > 95% | residual |

Duas guardas e uma correção de empate:

- **piso-edital** — `E(n) ≥ 0.80` nunca fica em D. Cai pouco, mas é obrigatório: um item que
  quase todo edital cobra pode ser justamente o que aparece na sua prova.
- **promover_se_confirmado** — `C(n) < 0.30` não sustenta classe A sozinho; desce para B com a
  flag. Um tópico que apareceu 2 vezes por sorte não deve mandar no cronograma.
- **empate** — nós com peso idêntico recebem a mesma classe (a melhor do grupo).

## 10. Custo e ROI

`custo_h` é a única entrada estimada pelo modelo, não medida. Âncoras para calibrar:

| horas | perfil do conteúdo |
|---|---|
| 0.5–1 | conceito único, cobrado em letra de lei |
| 1–2 | tópico fechado com poucas exceções |
| 2–4 | tópico com jurisprudência ou cálculo |
| 4–8 | subsistema inteiro (ex.: processo de licitação ponta a ponta) |

```
roi(n) = 100 · (peso(n)/custo_h(n)) / max(peso/custo_h no nível)
```

Serve ao plano de estudos quando o tempo é curto: peso responde "o que mais cai", ROI responde
"o que rende mais por hora investida". São perguntas diferentes e frequentemente dão respostas
diferentes.

## 11. Arestas derivadas

- **`contem`** — força = `I_sub(filho) / I_sub(pai)`: a fatia da carga do pai que o filho carrega.
- **`coocorre`** — Jaccard sobre os conjuntos de questões: `|Q(a) ∩ Q(b)| / |Q(a) ∪ Q(b)|`.
  Registrada com no mínimo 2 questões em comum e J ≥ 0.15. Indica assuntos que a banca cobra
  na mesma questão — candidatos naturais a estudar juntos.

---

## 12. Exemplo completo, conferível

Cenário: 2 editais (FGV 2026, FCC 2024), 3 provas úteis (FGV 2026, FGV 2024, FCC 2022), banca-alvo
FGV, janela 2022–2026. Uma quarta prova falhou no download e foi excluída.

Ramo `T.1` com três tópicos; ramo `T.2` com dois.

| nó | I_sub | E | I_aj_norm | tend. | bruto | **peso** | classe | conf | custo | roi |
|---|---|---|---|---|---|---|---|---|---|---|
| T.1.1 | 6.010 | 1.00 | 1.000 | alta ×1.15 | 1.150 | **100** | A | 0.72 | 3.0 h | 78 |
| T.1.2 | 3.881 | 1.00 | 0.723 | queda ×0.88 | 0.722 | **63** | A | 0.72 | 2.0 h | 73 |
| T.1.3 | 0.000 | 1.00 | 0.217 | indef. | 0.491 | **43** | C | 0.30 | 1.0 h | 100 |
| T.2.1 | 1.723 | 0.00 | 0.261 | indef. | 0.170 | **15** | C | 0.26 | 0.5 h | 70 |
| T.2.2 | 0.574 | 0.00 | 0.190 | indef. | 0.123 | **11** | D | 0.12 | 4.0 h | 6 |

Três leituras que só aparecem porque os componentes são separados:

- **T.1.3 nunca caiu** e ainda assim vale 43 — está nos dois editais. O encolhimento o segura
  em 0.217 de incidência ajustada (não em zero, nem no patamar dos irmãos), e o componente
  editalício faz o resto. É o tópico de maior **ROI** do conjunto: 1 hora e pode cair.
- **T.1.2 tem a mesma amostra de T.1.1** (7,5 questões) mas pesa 63 contra 100 — as questões
  dele estão nas provas antigas, e a tendência de queda o desconta.
- **T.2.2 tem confiança 0.12.** O peso 11 é chute educado, não medição. O grafo diz isso na
  cara, em vez de esconder atrás de um número de aparência precisa.

Para reproduzir: `scripts/grafo.py build <slug>` sobre a fixture correspondente.

---

## 13. Quando mexer nos parâmetros

Os padrões servem para concurso brasileiro típico. Ajustar em `evidencias.json → parametros`
(vale para o grafo inteiro) ou em `ajustes.json` (sobrescreve tudo).

| situação | parâmetro | direção |
|---|---|---|
| Área com legislação estável (português, RLM) | `meia_vida_anos` | ↑ 4.0 — prova antiga continua valendo |
| Área que mudou de lei há pouco | `meia_vida_anos` | ↓ 1.5 — o passado engana |
| Concurso com banca já definida em edital | `peso_outras_bancas` | ↓ 0.25 |
| Banca ainda indefinida | `banca_alvo: []` | todas pesam igual |
| Edital novíssimo, poucas provas dele | `w_edital` | ↑ 0.50 |
| Amostra grande e confiável | `w_edital` | ↓ 0.25 — deixe os dados falarem |
| Muitos tópicos com 1–2 questões | `m_prior_ramo` | ↑ 8.0 — encolhe mais |
