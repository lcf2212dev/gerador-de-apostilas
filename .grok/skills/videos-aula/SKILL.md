---
name: videos-aula
description: >-
  Curadoria de aulas de referência: links de videoaula do QConcursos (se a conta
  estiver logada) e só vídeos YouTube que passam no padrão AAA, conferidos contra
  o YouTube antes de recomendar. Use quando o usuário pedir vídeos, videoaulas,
  indicações no YouTube ou material complementar em vídeo. Também usada pela
  skill apostila para gerar videos.json.
---

# Aulas de referência — QC + YouTube AAA

Duas prateleiras no mesmo `videos.json`. **Nunca preencher cota.**

1. **QConcursos** (se `qc.py status` logado): até 5 videoaulas da plataforma no assunto.
   Não passam por `yt.py`. Sem score AAA. Cota vazia é resultado legítimo.
2. **YouTube**: só o que passa no corte AAA (85), no máximo 5. Sem QC, esta prateleira
   segue sozinha.

## Fluxo

0. **QC, se houver conta.** Skill `qconcursos`:
   ```
   .venv/bin/python .grok/skills/qconcursos/scripts/qc.py aulas --disciplina "…" --assunto "…" --max 8
   ```
   Entre os que aderirem à aula, grave até 5 com `origem: "qconcursos"`, `url`, `titulo`,
   `canal` (professor/curso), `por_que`, `verificado_em`. Sem `yt.py`.

1. **Montar 2 a 4 consultas YouTube** com vocabulários diferentes — o termo técnico, o número do
   dispositivo, o nome popular do assunto, e a variante com "concurso" ou "resumo".
2. **Buscar candidatos:**
   ```
   python3 .grok/skills/videos-aula/scripts/yt.py buscar "sua consulta" --max 20
   ```
   Os números da saída são reais, raspados da página de resultados.
3. **Filtrar pelos eliminatórios** (abaixo) só com o que a busca já mostrou — isso descarta a
   maior parte sem custo.
4. **Inspecionar os finalistas** (5 a 8 candidatos):
   ```
   python3 .grok/skills/videos-aula/scripts/yt.py inspecionar ID1 ID2 ID3 --json
   ```
   Traz data exata de publicação, contagem de inscritos do canal, duração e disponibilidade.
   **Nenhum YouTube entra sem passar por aqui.** QC não usa `yt.py`.
5. **Pontuar** cada YouTube pela rubrica de `references/criterios-aaa.md`. Corte em **85**.
6. **Escrever `videos.json`**: QC primeiro, depois YouTube por score decrescente.

Se a busca falhar (o HTML do YouTube muda de tempos em tempos), use a ferramenta `WebSearch`
para descobrir candidatos e **mesmo assim** rode `inspecionar` em cada id antes de recomendar.

## Eliminatórios — reprovam de imediato

- Vídeo indisponível, privado, removido ou não incorporável (o `inspecionar` acusa).
- Short, ou duração abaixo de 6 min — não cabe explicação de conteúdo de concurso.
- Duração acima de 90 min, salvo pedido explícito de aula longa.
- Transmissão ao vivo não editada.
- Idioma diferente de português do Brasil, salvo pedido em contrário.
- Isca de curso: o vídeo é anúncio com 5 minutos de conteúdo e 20 de venda.
- Canal agregador sem autoria identificável, narração sintética sobre slides genéricos,
  compilado de cortes.
- Conteúdo superado por mudança de lei, súmula ou entendimento posterior à publicação.

## Contrato — `videos.json`

```json
{
  "consulta": ["termos usados na busca"],
  "videos": [
    {
      "origem": "qconcursos",
      "id": "playlist-seguridade-social",
      "url": "https://www.qconcursos.com/playlist/…",
      "titulo": "título na plataforma",
      "canal": "professor ou curso QC",
      "por_que": "o que esta aula da plataforma acrescenta",
      "verificado_em": "2026-08-17"
    },
    {
      "origem": "youtube",
      "id": "Vvs6d22g4eM",
      "url": "https://youtu.be/Vvs6d22g4eM",
      "titulo": "título exato como está no YouTube",
      "canal": "nome do canal",
      "duracao_min": 34.7,
      "visualizacoes": 61133,
      "publicado": "2025-04-23",
      "score_aaa": 91,
      "criterios": {"autoridade": 27, "aderencia": 24, "didatica": 14, "engajamento": 13, "atualidade": 13},
      "por_que": "uma frase dizendo o que este vídeo resolve para quem acabou de ler a aula",
      "trecho_recomendado": "04:10–22:40",
      "verificado_em": "2026-08-17"
    }
  ]
}
```

- YouTube: `titulo` e `canal` vêm do `inspecionar`. Sem `inspecionar`, não entra.
- QC: `url` canônica; `id` pode ser o slug. `origem: "qconcursos"`.
- `origem` omitida conta como YouTube (aulas antigas).
- `por_que` fala com quem acabou de estudar: o que aquele item acrescenta.
- `trecho_recomendado` é opcional (YouTube longo).

## Como relatar

Quantos QC, quantos YouTube examinados/aprovados, e por que os descartados caíram. Prateleira
vazia: deixe vazia e explique — a apostila não inventa item.
