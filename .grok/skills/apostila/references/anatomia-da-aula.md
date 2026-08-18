# Anatomia da aula

A ordem dos blocos é fixa. O que muda de aula para aula é o conteúdo, nunca a forma — é a
repetição da forma que deixa o estudante saber onde procurar cada coisa sem pensar.

## Cabeçalho e objetivos (gerados a partir do `meta.json`)

**Objetivos** — três, no máximo quatro, sempre com verbo observável: *distinguir*, *aplicar*,
*identificar*, *resolver*. Nunca "compreender" ou "conhecer", que não se verificam.

> Distinguir fundamentos, objetivos e princípios das relações internacionais.
> Reconhecer as pegadinhas que trocam o rol do art. 1º pelo do art. 3º.

Os objetivos precisam corresponder ao que as 10 questões cobram. Se uma questão mede algo que
nenhum objetivo anuncia, ou o objetivo está faltando, ou a questão está fora do escopo.

**Pré-requisitos** — só o que é de fato necessário, com o número da aula anterior quando houver.
Nada de listar a disciplina inteira.

## Corpo: 3 a 6 seções

Menos de 3 seções indica tema fino demais; mais de 6, aula que devia ser duas.

Cada seção segue o arco didático detalhado em `references/didatica.md`:

1. **Ponte** (1 frase) — o que a seção anterior deixou pronto para esta.
2. **Situação concreta** — o caso, o problema ou a pergunta que o conteúdo resolve.
3. **A regra**, com o dispositivo.
4. **Por que a regra é assim** — a razão por trás dela.
5. **Exemplo** (`.exemplo`) — obrigatório em toda seção.
6. **Onde as pessoas erram** — a confusão típica e sua origem.
7. **Checkpoint** — duas afirmações auto-verificáveis, no indicativo.

Caixas de sinalização entram no meio disso, no máximo uma a cada ~250 palavras. Os blocos
didáticos (`.exemplo`, `.em-outras-palavras`, `.passo-a-passo`) não têm limite.

Ordene as seções por **dependência**, não por importância: o que precisa ser entendido primeiro
vem primeiro. Prioridade se resolve na quantidade de espaço dedicada, não na ordem.

### Onde cada caixa entra

- **Lei seca** logo antes ou depois da explicação do dispositivo — nunca no lugar dela.
  Transcreva o texto exato; se for longo, corte com `[…]` mantendo o que a prova cobra.
- **Ponto-chave** no fim do raciocínio, consolidando. Não abra a seção com ele.
- **Pegadinha** junto do ponto que a banca explora, não num bloco de pegadinhas no fim.
- **Mnemônico** imediatamente depois do rol que ele memoriza.
- **Pare e responda** uma ou duas vezes por aula, no meio do conteúdo, cobrando o que acabou de
  ser apresentado. Nunca duas seguidas.

### O tom

Escreva para alguém inteligente que ainda não conhece o assunto e tem prova marcada. Direto,
segunda pessoa quando fizer sentido ("repare que", "guarde essa diferença"), sem enrolação
acadêmica e sem infantilizar. Frases curtas. Voz ativa.

Não anuncie programação ("nesta seção veremos") — mas **amarre** a seção na anterior, o que é
diferente: a ponte é conteúdo, o anúncio é enchimento.

O critério que decide tudo: **em nenhum ponto o leitor pode travar**. Leia o que escreveu
fingindo que nunca viu o assunto; onde você precisar supor algo que o texto não deu, falta
explicação. `references/didatica.md` traz as dez regras que sustentam isso.

## Fechamento

**Quadro-síntese**: uma linha por seção, com o dispositivo e a ideia central. É o que o
estudante relê no dia da prova. Se uma linha não couber em uma frase, a seção não estava clara.

Depois dele, `montar.py` acrescenta as fontes consultadas e o rodapé de identidade.
A revisão fica nos flashcards, não numa faixa D+1/D+7/D+30.

## Coerência entre os quatro produtos

A aula, as questões, os vídeos e os flashcards precisam falar da mesma coisa:

| produto | relação com o conteúdo |
|---|---|
| 10 questões | toda seção com ao menos uma; nenhuma cobra o que a aula não ensinou |
| gabarito | cada comentário aponta a seção de origem |
| vídeos | complementam ou aprofundam; não substituem a leitura |
| 5 flashcards | só o que precisa ser recuperado de memória, distribuído entre as seções |

O teste final: um estudante que leu só a apostila consegue acertar as 10 questões? Se não, ou o
conteúdo tem buraco, ou a questão saiu do escopo.
