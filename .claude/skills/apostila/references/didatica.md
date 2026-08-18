# Como escrever para quem ainda não sabe

Este é o documento mais importante da skill. A apostila não é um resumo para quem já domina o
assunto — é uma aula para quem está vendo aquilo pela primeira vez e tem prova marcada.

O erro típico do material de concurso é **listar em vez de ensinar**: o texto enuncia a regra,
cita o artigo, segue adiante. Quem já sabe, reconhece. Quem não sabe, decora sem entender e
erra na primeira questão que muda a roupagem.

O critério de qualidade é um só: **em nenhum ponto da aula o leitor trava**. Se ele precisa
parar, reler ou buscar em outro lugar para continuar, o texto falhou ali.

---

## As onze regras

### 1. Nenhum termo órfão

Todo termo técnico é explicado **na primeira vez que aparece**, ali mesmo, em linguagem comum.
Não vale mandar o leitor procurar depois, nem supor que ele viu na aula anterior.

> Ruim: "A norma é de eficácia contida."
> Bom: "A norma é de eficácia contida — ou seja, ela já produz efeitos desde a promulgação,
> mas uma lei posterior pode restringir seu alcance."

### 2. Do concreto para o abstrato

Abra com a situação, depois nomeie a regra. O cérebro ancora o conceito novo em algo que já
conhece; sem âncora, a definição escorrega.

> Ruim: "A eficácia horizontal significa a incidência dos direitos fundamentais nas relações
> privadas."
> Bom: "Uma associação expulsou um sócio sem deixá-lo se defender. O STF anulou a expulsão,
> mesmo tratando-se de entidade privada. É o que se chama eficácia horizontal: os direitos
> fundamentais valem também entre particulares, não só contra o Estado."

### 3. Um conceito por parágrafo

Parágrafo de 3 a 6 linhas, com uma ideia. Dois conceitos no mesmo bloco fazem o leitor perder
o primeiro enquanto processa o segundo.

### 4. Todo conceito abstrato tem exemplo concreto

Use o bloco `.exemplo`. Exemplo bom tem gente, número, situação — não "por exemplo, quando
ocorre a hipótese legal". Prefira o exemplo que a banca usaria.

Regra prática: **toda seção precisa de pelo menos um exemplo**. O verificador avisa quando falta.

### 5. Explique o porquê antes de mandar decorar

Quem entende a razão da regra reconhece a regra mesmo quando a questão a disfarça. Quem só
decorou depende de a banca repetir a redação.

> "A iniciativa popular exige assinaturas de cinco Estados diferentes. A razão é evitar que
> uma única região, concentrando eleitorado, imponha pauta legislativa ao país inteiro."

### 6. Antecipe a confusão

Diga com o que o conceito costuma ser confundido — e **por que** a confusão acontece. Isso vale
mais que a advertência seca de que "não confunda".

> "Soberania aparece duas vezes no art. 1º e as duas não são a mesma coisa. No inciso I, é
> atributo do Estado diante de outros Estados. No parágrafo único, 'soberania popular' responde
> a outra pergunta: de quem é o poder aqui dentro. O nome se repete, o conceito não."

Isso vale quando a confusão é **real**: a banca já cobrou, ou há dois conceitos que de fato
se misturam. Seção sem pegadinha conhecida não ganha uma inventada — advertência sem inimigo
é ruído.

### 7. Nunca pule etapa de raciocínio

Quando a conclusão exige duas ou mais inferências, use `.passo-a-passo` e mostre cada uma.
O que é óbvio para quem escreve costuma ser o degrau que falta para quem lê.

### 8. Amarre cada seção na anterior

Uma frase de ponte no começo da seção, ligando ao que acabou de ser visto. Ponte é conteúdo
("os fundamentos dizem sobre o que o Estado se apoia; agora veremos quem exerce o poder que
eles sustentam"), não anúncio de programação ("nesta seção estudaremos o parágrafo único").

A ponte tem **uma frase**, e só existe quando a seção usa o que a anterior construiu. Assunto
que muda de bloco entra direto pela situação concreta. Se a ponte precisa de duas frases, o
problema é a ordem das seções, não a ponte.

### 9. Linguagem que não atrapalha

- Frases curtas. Média de até 20 palavras; acima de 35, quebre.
- Voz ativa. "A Constituição veda", não "é vedado pela Constituição".
- Segunda pessoa quando ajudar: "repare que", "guarde essa diferença".
- Zero juridiquês decorativo: nada de "outrossim", "destarte", "cumpre salientar", "insta
  consignar". Se a palavra existe só para soar formal, corte.
- Ordem direta: sujeito, verbo, complemento. Evite a oração intercalada de três linhas.

### 10. Reformule só o que é genuinamente denso

Depois de um trecho técnico **inevitável** — lei seca transcrita, definição doutrinária —,
traduza com `.em-outras-palavras`. O critério é duro: se o parágrafo já está em linguagem
comum, reformular é repetir; se a sua prosa ficou densa, reescreva a prosa em vez de anexar
a tradução. **No máximo 3 blocos por aula** — e nunca um por seção, por hábito.

### 11. Ensine uma vez, consolide uma — e pare

Cada ideia tem direito a **duas aparições** na aula: a de **ensino** (a prosa com seu exemplo —
o exemplo aplica a regra, não a reenuncia) e a de **consolidação** (ponto-chave, linha da
síntese OU flashcard — **um** deles, nunca os três com a mesma frase). A terceira aparição
não fixa: dilui. Em concreto:

- **Um exemplo por conceito.** O segundo só entra se mudar a resposta (exceção, inversão de
  resultado). Outro caso igual não ensina nada novo.
- **Depois do exemplo, avance.** Não reafirme a regra que o exemplo acabou de aplicar —
  "ou seja", "como vimos", "em resumo" no meio da seção anunciam repetição.
- **Contexto histórico só quando cai em prova.** A emenda que mudou a regra entra; a biografia
  da instituição, não.
- **Ponto-chave não repete parágrafo**: ou condensa em uma frase um raciocínio que se estendeu
  por vários, ou não existe. No máximo um por seção.
- A revisão didática (`estimar_tempo.py`) acusa formulação repetida 3+ vezes; o revisor
  devolve aula com eco.

---

## O arco de cada seção

Núcleo obrigatório, nesta ordem:

1. **Âncora** — a situação concreta, o caso ou a pergunta que o conteúdo resolve (1 a 3 frases).
2. **A regra**, com o dispositivo.
3. **Por que a regra é assim** — 1 a 2 frases; é o que faz reconhecer a regra disfarçada.
4. **Exemplo** — um por conceito, com gente, número e situação.

Opcionais, cada um com critério de entrada:

- **Ponte** (1 frase, antes da âncora) — só quando a seção depende da anterior.
- **Onde erram** — só quando a confusão existe de verdade (regra 6).
- **Passo-a-passo** — quando a conclusão exige duas ou mais inferências (regra 7).

O que saiu do arco: o **checkpoint por seção**. A aula tem um único checkpoint, antes da
síntese (ver `anatomia-da-aula.md`). O que não falta em nenhuma seção: o **exemplo**.

---

## Antes e depois

**Antes** (lista, não ensina):

> Os Municípios não possuem Poder Judiciário, organizando-se apenas em Executivo e Legislativo,
> por força do princípio da simetria aplicado no que couber.

**Depois** (ensina):

> Imagine um prefeito criando o "Tribunal de Justiça de sua cidade". Não pode — e a razão
> ajuda a lembrar: a Constituição organiza a Justiça em ramos estaduais e federais, e nenhum
> deles é municipal. Por isso, o Município tem só dois Poderes: Executivo (prefeito) e
> Legislativo (câmara de vereadores).
>
> O que confunde é o **princípio da simetria**, a regra de que os entes menores reproduzem o
> modelo federal. Ele existe, mas vale "no que couber" — e um Judiciário municipal não cabe,
> porque a própria Constituição não previu esse ramo.

O segundo trecho é mais longo porque ensina o que o primeiro só enunciava — e esse preço se
paga **uma vez, no primeiro encontro com o conceito**. O que o orçamento não paga é dizer de
novo o que já foi ensinado: profundidade custa palavras, repetição só custa. Cobrir muito e
ensinar pouco é o que esta skill não faz; ensinar uma vez e repetir seis é o outro defeito
que ela também não comete.

---

## O que NÃO é ser didático

- Infantilizar, encher de exclamação ou de "viu só como é fácil?".
- Repetir a mesma frase com outras palavras sem acrescentar nada.
- Encher de analogia até o conteúdo jurídico sumir. Uma analogia por conceito difícil, e sempre
  dizendo onde ela deixa de valer.
- Trocar precisão por simplicidade. Se a simplificação vira erro, ela não é didática — é falsa.
  Nesse caso, simplifique a **explicação**, nunca o conteúdo.
- Cortar o dispositivo legal. O estudante precisa da letra da lei; o que ele não precisa é
  receber só a letra da lei.
- Repetir em camadas: enunciar na prosa, reenunciar no ponto-chave, reenunciar na síntese e
  de novo no flashcard. Sinalização que repete o texto não é reforço — é a mesma frase
  gastando a atenção quatro vezes.
