# Anatomia da aula

A ordem dos blocos é fixa. O que muda de aula para aula é o conteúdo, nunca a forma — é a
repetição da forma que deixa o estudante saber onde procurar cada coisa sem pensar.

## Cabeçalho e objetivos (gerados a partir do `meta.json`)

**Objetivos** — dois ou três, sempre com verbo observável: *distinguir*, *aplicar*,
*identificar*, *resolver*. Nunca "compreender" ou "conhecer", que não se verificam.
Objetivo cobre a aula, não uma seção: se cada seção tem um objetivo espelhado, o bloco
virou um segundo mapa da aula.

> Distinguir fundamentos, objetivos e princípios das relações internacionais.
> Reconhecer as pegadinhas que trocam o rol do art. 1º pelo do art. 3º.

Os objetivos precisam corresponder ao que as 10 questões cobram. Se uma questão mede algo que
nenhum objetivo anuncia, ou o objetivo está faltando, ou a questão está fora do escopo.

**Pré-requisitos** — só o que é de fato necessário, com o número da aula anterior quando houver.
Nada de listar a disciplina inteira.

**Mapa da aula** — o mapa é gerado dos `<h2>`: uma linha por seção, custo zero de
redundância autoral.

## Corpo: 3 a 5 seções

Cada seção carrega 2 a 3 unidades de conteúdo. Menos de 3 seções, tema fino demais;
mais de 5, aula que devia ser duas.

Cada seção segue o arco de `references/didatica.md`: âncora, regra, porquê e exemplo
obrigatórios; ponte, erro típico e passo-a-passo por critério.

Caixas de sinalização entram no meio disso, no máximo uma a cada ~400 palavras e dez por
aula. Os blocos didáticos (`.exemplo`, `.em-outras-palavras`, `.passo-a-passo`) não têm limite.

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

**Checkpoint da aula** — um único, imediatamente antes do quadro-síntese: 3 a 5 afirmações
auto-verificáveis, uma por seção, no indicativo ("sei…", "distingo…"). O checkpoint por
seção foi abolido: oito paradas de auto-teste picotavam a leitura e ensaiavam a síntese que
vinha três parágrafos depois.

**Quadro-síntese**: uma linha por seção, com o dispositivo e a ideia central. É o que o
estudante relê no dia da prova. Se uma linha não couber em uma frase, a seção não estava clara.
A linha da síntese não repete a frase do ponto-chave — se estão literalmente iguais, um dos
dois sobra (regra 11 de `didatica.md`).

Depois dele, `montar.py` acrescenta as fontes consultadas e o rodapé de identidade.
A revisão fica nos flashcards, não numa faixa D+1/D+7/D+30.

## Coerência entre os quatro produtos

A aula, as questões, os vídeos e os flashcards precisam falar da mesma coisa:

| produto | relação com o conteúdo |
|---|---|
| 10 questões | toda seção com ao menos uma; nenhuma cobra o que a aula não ensinou |
| gabarito | cada comentário aponta a seção de origem |
| vídeos | complementam ou aprofundam; não substituem a leitura |
| 5 flashcards | só o que precisa ser recuperado de memória, distribuído entre as seções; pergunta de recuperação, não recorte do texto: o card não repete frase de ponto-chave nem de síntese |

O teste final: um estudante que leu só a apostila consegue acertar as 10 questões? Se não, ou o
conteúdo tem buraco, ou a questão saiu do escopo.
