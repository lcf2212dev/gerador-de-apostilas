# Priorização — as fórmulas

Tudo aqui é calculado por `scripts/sumario.py`. Este arquivo existe para você **explicar** uma
nota ao usuário, decidir se vale mexer num parâmetro e reconhecer quando o resultado está
estranho porque o grafo é pobre, não porque a fórmula errou.

## O que já vem pronto do grafo

A skill `mapear-conteudo` entrega, por nó, números que **não se recalculam aqui**:

| campo | o que é |
|---|---|
| `peso` (0–100) | incidência com decaimento por ano, banca-alvo e edital, já combinados — **normalizado dentro de cada nível** |
| `share_pct` | fatia da carga total de questões do escopo — comparável entre quaisquer nós |
| `classe` (A–D) | A concentra os primeiros 50% da carga, B até 80%, C até 95%, D o resto |
| `edital` (0–1) | quanto o tópico é exigido pelos editais |
| `n_questoes`, `confianca`, `tendencia`, `custo_h` | amostra, solidez, direção e horas |

Refazer esse cálculo aqui seria duplicar a fonte da verdade e divergir dela na primeira mudança
de parâmetro. O sumário **consome**.

## O que esta skill acrescenta

### 1. Base de valor

O `peso` é a melhor base — mas só vale entre nós **do mesmo nível**, porque o topo de cada nível
é 100 por construção. Comparar um `tema` com peso 100 e um `subtopico` com peso 100 é comparar
duas normalizações diferentes. Por isso:

| situação | base usada | registrado em |
|---|---|---|
| todos os itens no mesmo nível, com `peso` | `peso / 100` | `parametros.base_de_valor: "peso"` |
| itens em níveis diferentes | `0,65 · share_normalizado + 0,35 · edital` | `"share+edital"` |
| sem `share_pct` | idem, com `n_questoes` no lugar | `"questoes+edital"` |
| sem peso, share, questões e edital | todos iguais | `"uniforme"` + aviso |

Os pesos 0,65/0,35 não são invenção desta skill: são os mesmos `w_incidencia`/`w_edital` do
grafo, lidos do front-matter quando existem.

### 2. Centralidade — quanto o tópico destrava

O grafo não calcula isto, e é o principal valor agregado do sumário.

PageRank sobre as arestas `prerequisito` **invertidas**. No grafo, a aresta vai do pré-requisito
(`de`) para o dependente (`para`); no passeio aleatório a massa precisa andar no sentido
contrário — do dependente para aquilo de que ele depende. Quem é pré-requisito de muita coisa
valiosa acumula massa.

- vetor de teleporte proporcional à **base de valor** (nó interno herda a soma das folhas);
- damping 0,85; nó sem saída devolve a massa ao teleporte; convergência por δ < 1e-12 ou 200
  iterações;
- ciclos não atrapalham o PageRank (só a fila, ver adiante);
- o item herda a centralidade dos ancestrais dividida pelo número de folhas do ramo — um
  pré-requisito declarado no nível do tema vale para as folhas dele, repartido.

### 3. Valor composto e a escada de 1 a 10

```
V_bruto = (1 − β) · base + β · centralidade          β = 0,35 (padrão)
V       = V_bruto / máximo(V_bruto no recorte)       → (0, 1]
nota    = arredonda(10 · V^γ)                        γ = 1,0 (padrão), mínimo 1
```

Com γ = 1 a leitura é direta e verificável: **a nota é o valor do tópico em décimos do valor do
tópico mais forte daquele recorte**. 7/10 significa "vale 70% do que vale o topo desta lista".

Exemplo real, do fixture `scripts/testes/grafo-exemplo.md` (base = `peso`, β = 0,35):

| item | peso | base | centralidade | V_bruto | V | nota |
|---|---|---|---|---|---|---|
| Direitos individuais (art. 5º) | 100 | 1,00 | 0,79 | 0,9272 | 1,000 | **10** |
| Controle concentrado | 82 | 0,82 | 0,47 | 0,6971 | 0,752 | **8** |
| Administração pública | 74 | 0,74 | 0,40 | 0,6207 | 0,669 | **7** |
| Objetivos e fundamentos da República | 25 | 0,25 | 1,00 | 0,5125 | 0,553 | **6** |
| Relações internacionais | 12 | 0,12 | 0,18 | 0,1406 | 0,152 | **2** |

A quarta linha é a razão de a skill existir: "Objetivos e fundamentos" tem o 5º menor peso do
recorte e vale 6/10, porque é a maior centralidade da lista — destrava os direitos do art. 5º,
que destravam os remédios, os sociais, a nacionalidade e o controle concentrado. Um sumário
ordenado só por incidência colocaria isso no fim, e o aluno leria o art. 5º sem a base.

Quando explicar uma nota ao usuário, é isso que se diz: **quanto cai** e **o que destrava**.

### 4. Esforço: horas, aulas e o que é estimado

`custo_h` do grafo × 60 = minutos. Sem `custo_h`, estima `30 + 90 · base`, arredondado em blocos
de 15 min, entre 30 e 240 — e marca `custo-estimado` no item e em `lacunas.md`.

O item vira `teto(minutos / 30)` aulas, nenhuma passando de 45 min (a faixa que a skill
`apostila` aceita). Um tópico de 3 h vira 6 aulas de 30 min.

### 5. A fila

Ordenação topológica (Kahn) sobre os pré-requisitos, projetados para o nível dos itens. Entre os
disponíveis, escolhe por:

```
ROI = V / horas^k        k = 0,5 (padrão)
```

O expoente é o detalhe que faz a fila ficar sensata. Com `k = 1` (ROI puro), um tópico marginal
de meia hora fura a fila na frente de um tópico central de 3 horas, porque é barato — e o plano
começa pelo irrelevante. Com `k = 0,5` o esforço continua contando, sem dominar.

Dois ajustes finos:

- **coesão** (0,15): o item que `coocorre` ou é `correlato` do item anterior ganha bônus no
  desempate. Estudar junto o que cai junto.
- **ciclo**: se os pré-requisitos formarem ciclo, a fila não trava — quebra pelo item de maior
  valor e registra o ciclo em `lacunas.ciclos`. Ciclo é defeito do grafo, e aparece como tal.

Pré-requisito que mora fora do assunto pedido é **importado** com o ramo inteiro e vai para o
módulo 0 ("Base"). `--sem-prerequisitos` desliga isso.

### 6. Cobertura

Percorrendo a fila, acumula o `share` de cada item — renormalizado **dentro do recorte**, para
que "cobre 70% das questões" fale do assunto pedido, não do edital inteiro. A fatia que o
recorte representa do grafo completo fica em `totais.share_do_grafo`, e cada item guarda
`share_do_grafo` além do `share`.

## Parâmetros

| flag | padrão | mexer quando |
|---|---|---|
| `--beta` | 0,35 | `0` para ordenar só por incidência (grafo sem pré-requisito confiável); até 0,5 para prova que cobra raciocínio encadeado |
| `--gama` | 1,0 | < 1 espalha a base (mais itens com nota alta); > 1 endurece o topo |
| `--minutos-aula` | 30 | 20 para aulas curtas, 45 para blocos longos |
| `--coesao` | 0,15 | 0 para fila estritamente por ROI |
| `--cortes` | 0,50, 0,70, 0,90 | os marcos de cobertura exibidos |
| `--sem-prerequisitos` | desligado | quando o usuário quer só o recorte, sem a base |

Todo valor usado é gravado em `parametros` no `plano.json` e no front-matter do `sumario.md`.
Mudar parâmetro sem dizer por que, no sumário, é o mesmo que inventar número.

## Quando o resultado parece errado

| sintoma | causa provável |
|---|---|
| tudo com nota 9–10 | recorte pequeno e homogêneo — a escada é relativa ao topo do recorte |
| um tópico irrelevante no topo da fila | `custo_h` ausente ou subestimado; confira `lacunas.custo_estimado` |
| ordem "esquisita" | pré-requisito faltando no grafo — a fila só respeita o que está declarado |
| nota alta em tópico que não cai | é centralidade; baixe `--beta` ou confira se o pré-requisito declarado existe mesmo |
| cobertura não chega a 100% | itens sem `share_pct` nem `n_questoes` (ver `lacunas.sem_incidencia`) |
