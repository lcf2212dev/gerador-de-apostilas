---
name: apostila
description: >-
  Escreve uma aula completa em formato de apostila impressa — conteúdo didático de cerca de
  30 minutos de estudo (alvo do briefing ±5), layout azul e verde sobre branco pensado para
  papel, seguido de 10 questões
  de banca, gabarito comentado, vídeos do YouTube verificados e 5 flashcards prontos para o Anki.
  Gera HTML de arquivo único e PDF. Use quando o usuário pedir uma aula, apostila, material de
  estudo, resumo para imprimir, PDF de estudo sobre um assunto, ou disser "gera a aula N do
  sumário". Consome o plano de estudo de `montar-sumario` quando ele existe, e chama as skills
  `questoes-banca`, `videos-aula` e `flashcards-anki` para as páginas finais, e a skill
  `revisar-aula` antes de entregar. Para a apostila inteira de um assunto, use
  `curso-completo`. Com `.env` QConcursos, a skill `qconcursos` informa incidência e aulas
  da plataforma.
---

# Apostila

Uma aula = um arquivo HTML autossuficiente (CSS embutido) + um PDF, com esta anatomia fixa:

| bloco | onde |
|---|---|
| cabeçalho, objetivos, pré-requisitos, mapa da aula | primeira página |
| 3 a 5 seções de conteúdo, com caixas de sinalização | corpo |
| quadro-síntese, fontes consultadas | fim do conteúdo |
| **10 questões + cartão-resposta** | página nova |
| **gabarito comentado** | página nova |
| **Vídeo Aulas** | página nova |
| **5 flashcards recortáveis** | página nova |

**Divisão de trabalho: o modelo escreve, os scripts montam.** Você produz cinco arquivos-fonte;
`montar.py` compõe o documento. Nunca escreva o HTML completo à mão — o layout, a paginação e
as três páginas finais são gerados, e é isso que mantém todas as aulas idênticas em forma.

---

## O procedimento

### 1. Situar a aula

**Se existe um sumário de estudo** (`sumarios/<slug>/`, da skill `montar-sumario`), ele manda:
tema, título, objetivo, duração, pré-requisitos e prioridade já foram decididos a partir do
grafo de incidência. Não redecida nada disso.

```bash
python3 .claude/skills/apostila/scripts/contexto_aula.py sumarios/<slug> --listar          # que aulas existem
python3 .claude/skills/apostila/scripts/contexto_aula.py sumarios/<slug> --aula 3          # briefing da aula 3
python3 .claude/skills/apostila/scripts/contexto_aula.py sumarios/<slug> --aula 3 --meta > meta.json
```

`--aula N` usa a numeração do `grade.json`, em que um tópico grande já aparece fatiado em
várias aulas dentro da faixa. Havendo só `plano.json`, use `--num 5.1 --parte 2`.

**Sem plano**, você dimensiona a aula sozinho — regra em `references/orcamento-de-tempo.md`.
Anuncie a decisão em uma linha ("tema com 9 unidades de conteúdo → aula de ~38 min") e siga
sem perguntar. O usuário corrige se quiser.

### 2. Levantar o conteúdo

Material que o usuário forneceu vem primeiro. Norma em vigor: Planalto / portal da banca /
tribunal, com URL em `meta.json.fontes`. Dispositivo no texto: `CF/88, art. 5º, LXIII`.
Se o QC estiver logado, use-o para ver como a banca cobra — não como fonte da lei.

Antes de afirmar prazo, quórum ou redação de artigo, confirme que a norma continua em vigor.
Em concurso, informação desatualizada é pior que ausência de informação.

### 3. Escrever `corpo.html`

**Leia `references/didatica.md` antes de escrever a primeira linha.** É o documento que define
o padrão de qualidade desta skill: a apostila ensina quem nunca viu o assunto, não resume para
quem já sabe. Sem isso, o texto sai listando regras — que é exatamente o defeito do material de
concurso que esta skill existe para não repetir.

Só o fragmento das seções — sem `<html>`, sem `<style>`, sem cabeçalho, sem o quadro de
questões. Estrutura, blocos disponíveis e exemplo de cada um: `references/design-system.md`.
O que entra em cada parte da aula: `references/anatomia-da-aula.md`.

Confira tamanho **e didática** enquanto escreve:
```bash
python3 .claude/skills/apostila/scripts/estimar_tempo.py --alvo 30 --orcamento     # quantas palavras e unidades cabem
python3 .claude/skills/apostila/scripts/estimar_tempo.py corpo.html --alvo 30      # onde você está + revisão didática
```

A revisão didática aponta seção sem exemplo concreto, parágrafo-parede, frase arrastada e
juridiquês decorativo. São avisos, não erros — mas cada um marca um lugar onde o leitor trava.
Trate-os até a revisão sair limpa.

### 4. Páginas finais

Invoque as três skills, nesta ordem, e grave os JSONs no mesmo diretório:

| skill | saída | validação |
|---|---|---|
| `questoes-banca` | `questoes.json` | `validar_questoes.py questoes.json --corpo corpo.html` |
| `videos-aula` | `videos.json` | QC = link da conta; YouTube = `yt.py inspecionar` + AAA |
| `flashcards-anki` | `flashcards.json` | 5 cards, atômicos |

### 5. Montar e conferir

```bash
python3 .claude/skills/apostila/scripts/montar.py --dir aulas/<disciplina>/aula-NN-<slug>
bash .claude/skills/apostila/scripts/gerar_pdf.sh aulas/<disciplina>/aula-NN-<slug>/<slug>.html
```

`montar.py` valida os contratos, escreve o HTML e imprime o relatório de tempo. Fora de
20–45 min ele sai com erro — mas o alvo de produção é o do briefing ±5: ajuste o corpo e
monte de novo. Durante a redação, `--parcial` monta uma prévia sem as páginas finais.

### 6. Revisar e fechar

Invoque a skill `revisar-aula` no diretório. Sem aprovação, a aula não está pronta.
Aprovada: feche a pasta — **só o PDF fica no disco**:

```bash
python3 .claude/skills/apostila/scripts/fechar_aula.py --dir aulas/<disciplina>/aula-NN-<slug>
```

Ofereça o import no Anki e entregue o caminho do PDF. Tempo de conteúdo: **no terminal,
nunca no documento**. Sem faixa D+1/D+7/D+30, sem data de geração, sem comando cru do Anki.

---

## Os cinco arquivos-fonte

Em `aulas/<disciplina>/aula-NN-<slug>/`:

| arquivo | quem escreve | conteúdo |
|---|---|---|
| `meta.json` | você (ou `contexto_aula.py --meta`) | identificação, objetivos, pré-requisitos, fontes |
| `corpo.html` | você | as seções da aula |
| `questoes.json` | skill `questoes-banca` | 10 itens com gabarito comentado |
| `videos.json` | skill `videos-aula` | QC (links) + YouTube AAA |
| `flashcards.json` | skill `flashcards-anki` | 5 cards |

`meta.json` mínimo: `disciplina`, `numero`, `titulo`, `slug`, `objetivos`. Opcionais úteis:
`subtitulo`, `pre_requisitos`, `banca_estilo` (padrão `A-E`), `duracao_alvo_min`,
`margem_anotacao` (padrão `false`), `fontes`, `plano`.

---

Use o modelo da sessão do início ao fim. Sem troca de modelo no meio.

---

## Regras inegociáveis

1. **A aula ensina, não resume.** Nenhum conceito abstrato sem exemplo concreto; nenhum termo
   técnico sem explicação na primeira aparição; a razão da regra antes da ordem de decorar.
   Se o leitor precisa parar e buscar em outro lugar para continuar, o texto falhou —
   `references/didatica.md`. Na dúvida entre cobrir mais assunto e ensinar melhor, **ensine
   melhor**: o que sobrar vira a próxima aula.
2. **O tempo nunca aparece na apostila.** Nem no cabeçalho, nem no mapa da aula, nem por seção.
   É restrição de projeto e relatório de terminal — o estudante não deve estudar com cronômetro
   na cabeça.
3. **Alvo do briefing ±5 min (padrão 30)**; a trava do montador é 20–45. Questões, gabarito
   e flashcards são extras e não entram na conta. Tema grande vira duas aulas; aula curta
   (20–30) só quando o sumário mandar.
4. **Branco domina.** Cor só em filetes, ícones e fundos claros. Nada de bloco escuro: gasta
   toner e piora a leitura no papel.
5. **No máximo uma caixa a cada ~400 palavras e dez por aula.** Sinalização em excesso
   destrói a atenção que deveria criar. O validador de tempo avisa quando a densidade passa
   do ponto.
6. **Nunca escreva o HTML final à mão** nem edite o `.html` gerado — a próxima montagem apaga.
   Corrija a fonte e remonte.
7. **Fonte para toda afirmação normativa**, com o dispositivo citado no texto e a referência
   em `meta.json.fontes`.
8. **Nada de emoji** no documento: os ícones são SVG do CSS, que imprimem nítidos em qualquer
   impressora.
9. **Cada ideia aparece no máximo duas vezes**: uma para ensinar, uma para consolidar.
   O validador acusa repetição literal; o revisor devolve aula com eco.

---

## Recursos

| arquivo | quando ler |
|---|---|
| `references/didatica.md` | **leitura obrigatória**: como ensinar quem ainda não sabe |
| `references/anatomia-da-aula.md` | o que entra em cada bloco e em que ordem |
| `references/design-system.md` | classes CSS disponíveis, com exemplo de cada componente |
| `references/orcamento-de-tempo.md` | como dimensionar a aula e converter palavras em minutos |
| `scripts/contexto_aula.py` | briefing e `meta.json` a partir do plano de estudo |
| `scripts/estimar_tempo.py` | orçamento de palavras e conferência do tamanho |
| `scripts/montar.py` | monta o HTML único (`--parcial` para prévia) |
| `scripts/gerar_pdf.sh` | HTML → PDF via Chrome headless |
| `scripts/fechar_aula.py` | depois da aprovação, apaga fontes/HTML e deixa só o PDF |
