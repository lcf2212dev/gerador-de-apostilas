#!/usr/bin/env python3
"""Monta a apostila final (HTML único, CSS embutido) a partir dos arquivos-fonte.

Uso:
    python3 montar.py --dir aulas/<disciplina>/aula-NN-<slug> [--parcial] [--sem-qr]

Entrada, no diretório da aula:
    meta.json  corpo.html  questoes.json  videos.json  flashcards.json

Saída:
    <slug>.html  — arquivo único, imprimível em qualquer máquina
    relatório de tempo no terminal (nunca dentro do documento)
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from comum import (  # noqa: E402
    MAX_MINUTOS,
    MIN_MINUTOS,
    analisar_corpo,
    aviso,
    carregar_json,
    erro,
    esc,
    estimar_minutos,
    revisar_didatica,
    rich,
)

RAIZ_SKILL = Path(__file__).resolve().parent.parent
CSS = RAIZ_SKILL / "assets" / "apostila.css"
LETRAS = ("A", "B", "C", "D", "E")
NIVEIS = {"facil": "fácil", "media": "média", "dificil": "difícil"}


# --- Validação ------------------------------------------------------------


def validar_meta(meta: dict) -> None:
    obrigatorios = ("disciplina", "numero", "titulo", "slug", "objetivos")
    faltando = [c for c in obrigatorios if not meta.get(c)]
    if faltando:
        erro(f"meta.json sem os campos obrigatórios: {', '.join(faltando)}")
    if not isinstance(meta.get("objetivos"), list) or not meta["objetivos"]:
        erro("meta.json: 'objetivos' deve ser uma lista não vazia")


def validar_questoes(dados: dict, estilo: str) -> list:
    questoes = dados.get("questoes") or []
    if len(questoes) != 10:
        erro(f"questoes.json deve conter exatamente 10 questões (tem {len(questoes)})")
    for q in questoes:
        n = q.get("id", "?")
        if not q.get("enunciado"):
            erro(f"questão {n}: enunciado vazio")
        if not q.get("justificativa"):
            erro(f"questão {n}: sem justificativa do gabarito")
        if estilo == "cebraspe-ce":
            if q.get("gabarito") not in ("C", "E"):
                erro(f"questão {n}: no estilo Cebraspe o gabarito deve ser 'C' ou 'E'")
        else:
            alts = q.get("alternativas") or {}
            esperadas = LETRAS[: 4 if estilo == "A-D" else 5]
            if set(alts) != set(esperadas):
                erro(f"questão {n}: alternativas devem ser exatamente {', '.join(esperadas)}")
            if q.get("gabarito") not in esperadas:
                erro(f"questão {n}: gabarito '{q.get('gabarito')}' fora de {esperadas}")
    return questoes


def validar_flashcards(dados: dict) -> list:
    cards = dados.get("cards") or []
    if len(cards) != 5:
        erro(f"flashcards.json deve conter exatamente 5 cards (tem {len(cards)})")
    for i, c in enumerate(cards, 1):
        tipo = c.get("tipo", "basico")
        if tipo == "cloze":
            if "{{c" not in (c.get("texto") or ""):
                erro(f"card {i}: tipo cloze exige 'texto' com pelo menos um {{{{c1::…}}}}")
        elif not c.get("frente") or not c.get("verso"):
            erro(f"card {i}: tipo básico exige 'frente' e 'verso'")
    return cards


def validar_videos(dados: dict) -> list:
    videos = dados.get("videos") or []
    qc = [v for v in videos if v.get("origem") == "qconcursos"]
    yt = [v for v in videos if v.get("origem") != "qconcursos"]
    if len(qc) > 5:
        erro(f"videos.json aceita no máximo 5 aulas QConcursos (tem {len(qc)})")
    if len(yt) > 5:
        erro(f"videos.json aceita no máximo 5 vídeos YouTube (tem {len(yt)})")
    for v in qc:
        if not v.get("url") or not v.get("verificado_em"):
            erro(f"aula QC '{v.get('titulo', '?')}' sem 'url' ou sem 'verificado_em'")
        if not v.get("id"):
            v["id"] = (v.get("url") or "").rstrip("/").split("/")[-1] or "qc"
    for v in yt:
        if not v.get("id") or not v.get("verificado_em"):
            erro(f"vídeo '{v.get('titulo', '?')}' sem 'id' ou sem 'verificado_em' — "
                 "YouTube precisa passar por videos-aula/scripts/yt.py inspecionar")
    return videos


# --- Blocos ---------------------------------------------------------------


def render_cabecalho(meta: dict) -> str:
    subtitulo = meta.get("subtitulo", "")
    return f"""<header class="cabecalho-aula">
  <div class="faixa"></div>
  <div class="linha-superior">
    <span>{esc(meta['disciplina'])}</span>
    <span class="aula-num">Aula {int(meta['numero']):02d}</span>
  </div>
  <h1>{rich(meta['titulo'])}</h1>
  {f'<p class="subtitulo">{rich(subtitulo)}</p>' if subtitulo else ''}
</header>"""


def render_objetivos(meta: dict) -> str:
    itens = "\n".join(f"    <li>{rich(o)}</li>" for o in meta["objetivos"])
    bloco = f"""<section class="objetivos">
  <h2>Ao final desta aula você será capaz de</h2>
  <ul>
{itens}
  </ul>
</section>"""
    pre = meta.get("pre_requisitos") or []
    if pre:
        itens_pre = "\n".join(f"    <li>{rich(p)}</li>" for p in pre)
        bloco += f"""
<section class="pre-requisitos">
  <h2>Antes de começar</h2>
  <ul>
{itens_pre}
  </ul>
</section>"""
    return bloco


def render_mapa(titulos: list) -> str:
    numerados = [t for t in titulos if t["numerado"]]
    if not numerados:
        return ""
    itens = "\n".join(f"    <li><span>{rich(t['texto'])}</span></li>" for t in numerados)
    return f"""<nav class="mapa-aula">
  <h2>Mapa da aula</h2>
  <ol>
{itens}
  </ol>
</nav>"""


def render_fontes(meta: dict) -> str:
    fontes = meta.get("fontes") or []
    if not fontes:
        return ""
    itens = []
    for f in fontes:
        url = f.get("url", "")
        linha = f"<li>{rich(f.get('titulo', ''))}"
        if url:
            linha += f'<br><span class="url">{esc(url)}</span>'
        itens.append(linha + "</li>")
    return f"""<section class="fontes">
  <h3>Fontes consultadas</h3>
  <ol>
    {chr(10).join('    ' + i for i in itens)}
  </ol>
</section>"""


def render_rodape(meta: dict) -> str:
    return f"""<footer class="rodape-aula">
  <span>{esc(meta['disciplina'])} — Aula {int(meta['numero']):02d}: {esc(meta['titulo'])}</span>
</footer>"""


def render_pagina_questoes(questoes: list, estilo: str) -> str:
    letras = ("C", "E") if estilo == "cebraspe-ce" else LETRAS[: 4 if estilo == "A-D" else 5]

    itens_cartao = []
    for i in range(1, len(questoes) + 1):
        bolhas = "".join(f'<span class="bolha">{l}</span>' for l in letras)
        itens_cartao.append(
            f'<span class="item"><span class="n">{i:02d}</span>{bolhas}</span>'
        )

    blocos = []
    for i, q in enumerate(questoes, 1):
        if estilo == "cebraspe-ce":
            alternativas = (
                '<ul class="alternativas">'
                '<li><span class="letra">C</span><span>Certo</span></li>'
                '<li><span class="letra">E</span><span>Errado</span></li>'
                "</ul>"
            )
        else:
            alts = q.get("alternativas", {})
            linhas = "".join(
                f'<li><span class="letra">{l}</span><span>{rich(alts[l])}</span></li>'
                for l in letras
                if l in alts
            )
            alternativas = f'<ul class="alternativas">{linhas}</ul>'
        blocos.append(
            f"""<article class="questao">
  <span class="num">{i}</span>
  <p class="enunciado">{rich(q['enunciado'])}</p>
  {alternativas}
</article>"""
        )

    return f"""<section class="pagina" id="questoes">
  <div class="titulo-pagina">
    <h2>Questões</h2>
    <span class="selo">{len(questoes)} itens · resolva antes de conferir</span>
  </div>
  <div class="cartao-resposta">
    <h3>Cartão-resposta</h3>
    <div class="grade">
      {''.join(itens_cartao)}
    </div>
  </div>
  {chr(10).join(blocos)}
</section>"""


def render_pagina_gabarito(questoes: list) -> str:
    cabecalho = "".join(f"<th>{i}</th>" for i in range(1, len(questoes) + 1))
    respostas = "".join(f"<td>{esc(q.get('gabarito', '?'))}</td>" for q in questoes)

    comentarios = []
    for i, q in enumerate(questoes, 1):
        meta_linha = []
        if q.get("nivel"):
            nivel = NIVEIS.get(q["nivel"], q["nivel"])
            meta_linha.append(f"Gabarito {esc(q.get('gabarito', '?'))} · {esc(nivel)}")
        else:
            meta_linha.append(f"Gabarito {esc(q.get('gabarito', '?'))}")
        if q.get("secao"):
            meta_linha.append(f"seção {esc(q['secao'])}")
        fonte = f'<span class="fonte">{rich(q["fonte"])}</span>' if q.get("fonte") else ""

        erros = q.get("erros") or {}
        lista_erros = ""
        if erros:
            itens = "".join(
                f"<li><b>{esc(k)}</b> — {rich(v)}</li>"
                for k, v in sorted(erros.items())
                if k != q.get("gabarito")
            )
            if itens:
                lista_erros = f'<ul class="erros">{itens}</ul>'

        comentarios.append(
            f"""<article class="comentario">
  <span class="num">{i}</span>
  <p class="cabeca"><span>{' · '.join(meta_linha)}</span>{fonte}</p>
  <p>{rich(q['justificativa'])}</p>
  {lista_erros}
</article>"""
        )

    return f"""<section class="pagina" id="gabarito">
  <div class="titulo-pagina">
    <h2>Gabarito comentado</h2>
    <span class="selo">confira só depois de responder</span>
  </div>
  <table class="gabarito-resumo">
    <thead><tr>{cabecalho}</tr></thead>
    <tbody><tr>{respostas}</tr></tbody>
  </table>
  {chr(10).join(comentarios)}
</section>"""


def _cartao_video(v: dict, qrs: dict) -> str:
    origem = v.get("origem") or "youtube"
    url_cheia = v.get("url") or (f"https://youtu.be/{v['id']}" if v.get("id") else "")
    if origem == "qconcursos":
        url_curta = re.sub(r"^https?://(www\.)?", "", url_cheia)[:72]
        selo = "QConcursos"
    else:
        url_curta = f"youtu.be/{v.get('id', '')}"
        selo = "YouTube"
    svg = qrs.get(url_cheia)
    qr = f'<div class="qr">{svg}</div>' if svg else '<div class="qr"><div class="sem-qr"></div></div>'
    meta_partes = [f'<span class="canal">{esc(v.get("canal") or selo)}</span>']
    if v.get("duracao_min"):
        meta_partes.append(f"{int(v['duracao_min'])} min")
    if v.get("publicado"):
        meta_partes.append(str(v["publicado"])[:7])
    if v.get("trecho_recomendado"):
        meta_partes.append(f"trecho {esc(v['trecho_recomendado'])}")
    return f"""<article class="video">
  {qr}
  <div class="dados">
    <p class="titulo">{rich(v.get('titulo', ''))}</p>
    <p class="meta">{' · '.join(meta_partes)}</p>
    <p class="porque">{rich(v.get('por_que', ''))}</p>
    <p class="link">{esc(url_curta)}</p>
  </div>
</article>"""


def render_pagina_videos(videos: list, qrs: dict) -> str:
    if not videos:
        return """<section class="pagina" id="videos">
  <div class="titulo-pagina">
    <h2>Vídeo Aulas</h2>
  </div>
  <p class="nota">Nenhum vídeo recomendado para este tema.</p>
</section>"""

    cartoes = [_cartao_video(v, qrs) for v in videos]
    return f"""<section class="pagina" id="videos">
  <div class="titulo-pagina">
    <h2>Vídeo Aulas</h2>
    <span class="selo">{len(videos)} indicações</span>
  </div>
  {chr(10).join(cartoes)}
</section>"""


def _cloze_frente(texto: str) -> str:
    """Converte {{c1::resposta}} em lacuna e {{c2::…}} em texto visível."""
    import re

    def sub(m):
        return '<span class="cloze">[' + "&nbsp;" * 14 + "]</span>"

    return re.sub(r"\{\{c\d+::(.*?)(?:::.*?)?\}\}", sub, texto)


def _cloze_verso(texto: str) -> str:
    import re

    return re.sub(
        r"\{\{c\d+::(.*?)(?:::.*?)?\}\}",
        lambda m: f'<span class="cloze">{m.group(1)}</span>',
        texto,
    )


def render_pagina_flashcards(dados: dict, cards: list, dir_aula: Path) -> str:
    deck = dados.get("deck") or ""
    blocos = []
    for c in cards:
        if c.get("tipo") == "cloze":
            frente = _cloze_frente(rich(c["texto"]))
            verso = _cloze_verso(rich(c["texto"]))
        else:
            frente = rich(c["frente"])
            verso = rich(c["verso"])
        extra = f'<p class="extra">{rich(c["extra"])}</p>' if c.get("extra") else ""
        blocos.append(
            f"""<article class="card-corte">
  <div class="frente">
    <p class="rotulo">Pergunta</p>
    <p>{frente}</p>
  </div>
  <div class="verso">
    <p class="rotulo">Resposta</p>
    <p>{verso}</p>
    {extra}
  </div>
</article>"""
        )

    return f"""<section class="pagina" id="flashcards">
  <div class="titulo-pagina">
    <h2>Flashcards</h2>
    <span class="selo">{len(cards)} cartões · recorte pela linha tracejada</span>
  </div>
  <div class="flashcards">
    <p class="instrucao">Para revisar no Anki, abra o aplicativo e peça:
    <b>importe os flashcards desta aula</b>.
    Os cards entram no baralho <b>{esc(deck)}</b>.</p>
    {chr(10).join(blocos)}
  </div>
</section>"""


# --- QR codes -------------------------------------------------------------


def gerar_qrs(urls: list, ativo: bool) -> dict:
    if not ativo or not urls:
        return {}
    script = RAIZ_SKILL / "scripts" / "qr.py"
    for cmd in (
        [sys.executable, str(script), *urls],
        ["uv", "run", "--quiet", "--with", "segno", "python", str(script), *urls],
    ):
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if r.returncode == 0 and r.stdout.strip():
                return json.loads(r.stdout)
        except (OSError, json.JSONDecodeError, subprocess.TimeoutExpired):
            continue
    aviso("QR codes indisponíveis (segno não instalado e uv sem rede) — imprimindo só as URLs")
    return {}


# --- Principal ------------------------------------------------------------


def main() -> None:
    ap = argparse.ArgumentParser(description="Monta a apostila em HTML único.")
    ap.add_argument("--dir", required=True, type=Path, help="diretório da aula")
    ap.add_argument("--saida", type=Path, help="caminho do HTML (padrão: <dir>/<slug>.html)")
    ap.add_argument("--parcial", action="store_true",
                    help="monta mesmo sem questões/vídeos/flashcards (prévia de layout)")
    ap.add_argument("--sem-qr", action="store_true", help="não gera QR codes dos vídeos")
    args = ap.parse_args()

    d: Path = args.dir
    if not d.is_dir():
        erro(f"diretório não encontrado: {d}")

    meta = carregar_json(d / "meta.json")
    validar_meta(meta)
    estilo = meta.get("banca_estilo", "A-E")

    corpo_arq = d / "corpo.html"
    if not corpo_arq.exists():
        erro(f"corpo.html não encontrado em {d}")
    corpo = corpo_arq.read_text(encoding="utf-8")
    analise = analisar_corpo(corpo)
    tempo = estimar_minutos(analise)

    def opcional(nome, validador, chave):
        caminho = d / nome
        if not caminho.exists():
            if args.parcial:
                aviso(f"{nome} ausente — montando parcial")
                return {}, []
            erro(f"{nome} não encontrado em {d} (use --parcial para uma prévia sem ele)")
        dados = carregar_json(caminho)
        return dados, validador(dados)

    dados_q, questoes = opcional("questoes.json", lambda x: validar_questoes(x, estilo), "questoes")
    dados_v, videos = opcional("videos.json", validar_videos, "videos")
    dados_f, cards = opcional("flashcards.json", validar_flashcards, "cards")

    urls = [v.get("url") or f"https://youtu.be/{v['id']}" for v in videos]
    qrs = gerar_qrs(urls, ativo=not args.sem_qr)

    partes = [
        render_cabecalho(meta),
        '<main class="corpo">',
        render_objetivos(meta),
        render_mapa(analise["titulos"]),
        corpo.strip(),
        render_fontes(meta),
        render_rodape(meta),
        "</main>",
    ]
    if questoes:
        partes.append(render_pagina_questoes(questoes, estilo))
        partes.append(render_pagina_gabarito(questoes))
    if videos:
        partes.append(render_pagina_videos(videos, qrs))
    if cards:
        partes.append(render_pagina_flashcards(dados_f, cards, d))

    css = CSS.read_text(encoding="utf-8")
    classe_body = "com-margem" if meta.get("margem_anotacao", False) else "sem-margem"
    titulo_doc = f"{meta['disciplina']} — Aula {int(meta['numero']):02d}: {meta['titulo']}"

    html_final = f"""<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(titulo_doc)}</title>
<style>
{css}
</style>
</head>
<body class="{classe_body}">
<div class="folha">
{chr(10).join(partes)}
</div>
</body>
</html>
"""

    saida = args.saida or d / f"{meta['slug']}.html"
    saida.write_text(html_final, encoding="utf-8")

    status = "OK" if tempo["dentro_da_faixa"] else "FORA DA FAIXA"
    c = analise["contagem"]
    print(f"apostila: {saida}")
    print(f"  seções ............ {c['secao']}")
    print(f"  palavras .......... {analise['palavras']}")
    print(f"  didática .......... {c['exemplo']} exemplos, {c['passo_a_passo']} passo-a-passo, "
          f"{c['em_outras_palavras']} reformulações")
    print(f"  sinalização ....... {c['box']} caixas, {c['tabela']} tabelas, "
          f"{c['pare_responda']} pare-e-responda, {c['checkpoint']} checkpoints")
    print(f"  tempo de conteúdo . {tempo['total']} min "
          f"(leitura {tempo['leitura']} + elementos {tempo['extras']}) — {status}")

    for d in revisar_didatica(analise):
        aviso(d)

    if not tempo["dentro_da_faixa"]:
        alvo = MIN_MINUTOS if tempo["total"] < MIN_MINUTOS else MAX_MINUTOS
        delta = (alvo - tempo["total"]) * 170
        verbo = "acrescente" if delta > 0 else "corte"
        print(f"  >> faixa exigida: {MIN_MINUTOS}–{MAX_MINUTOS} min. "
              f"{verbo} ~{abs(int(delta))} palavras no corpo.", file=sys.stderr)
        raise SystemExit(2)


if __name__ == "__main__":
    main()
