"""Utilidades compartilhadas pelos scripts da skill apostila.

Sem dependências externas: só a biblioteca padrão do Python.
"""

from __future__ import annotations

import html
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

# Tags inline permitidas dentro de strings JSON (enunciados, comentários, cards).
# Tudo o mais é escapado — evita que um "<" solto quebre o documento.
TAGS_INLINE = ("strong", "b", "em", "i", "u", "sup", "sub", "code", "abbr", "small")


def rich(texto: str) -> str:
    """Escapa o texto e devolve as tags inline permitidas ao formato original."""
    if texto is None:
        return ""
    esc = html.escape(str(texto), quote=False)
    for tag in TAGS_INLINE:
        esc = esc.replace(f"&lt;{tag}&gt;", f"<{tag}>")
        esc = esc.replace(f"&lt;/{tag}&gt;", f"</{tag}>")
    esc = re.sub(r"&lt;br\s*/?&gt;", "<br>", esc)
    esc = esc.replace('&lt;mark class="termo"&gt;', '<mark class="termo">')
    esc = esc.replace("&lt;/mark&gt;", "</mark>")
    return esc


def esc(texto: str) -> str:
    """Escape total, para atributos e textos que nunca contêm marcação."""
    return html.escape("" if texto is None else str(texto), quote=True)


def contar_palavras(texto: str) -> int:
    return len([p for p in texto.split() if any(c.isalnum() for c in p)])


class _ExtratorTexto(HTMLParser):
    """Extrai texto visível, conta elementos e mede a estrutura didática do corpo."""

    IGNORAR = {"script", "style"}
    BLOCOS = {
        "box": "box",
        "pare-responda": "pare_responda",
        "checkpoint": "checkpoint",
        "exemplo": "exemplo",
        "em-outras-palavras": "em_outras_palavras",
        "passo-a-passo": "passo_a_passo",
        "quadro-sintese": "quadro_sintese",
    }

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.partes: list[str] = []
        self.partes_autorais: list[str] = []   # exclui transcrição de lei
        self.contagem = dict.fromkeys(list(self.BLOCOS.values()) + ["tabela", "secao"], 0)
        self.titulos: list[dict] = []
        self.secoes: list[dict] = []      # uma entrada por seção numerada
        self.paragrafos: list[str] = []
        self._pilha_ignorar: list[str] = []
        self._h2_atual: dict | None = None
        self._p_atual: list[str] | None = None
        self._profundidade_quadro = 0
        self._profundidade_lei = 0
        self._profundidade_tabela = 0

    # -- helpers ----------------------------------------------------------

    def _registrar_na_secao(self, chave: str) -> None:
        if self.secoes:
            self.secoes[-1][chave] = self.secoes[-1].get(chave, 0) + 1

    # -- parser -----------------------------------------------------------

    def handle_starttag(self, tag, attrs):  # noqa: D102
        atributos = dict(attrs)
        classes = (atributos.get("class") or "").split()

        if tag in self.IGNORAR:
            self._pilha_ignorar.append(tag)
            return

        if "quadro-sintese" in classes:
            self._profundidade_quadro = 1
        elif self._profundidade_quadro:
            self._profundidade_quadro += 1

        # Transcrição de lei é literal e tabela não é prosa: contam como leitura,
        # mas ficam fora da revisão de estilo (frase longa, jargão, parágrafo-parede).
        if "lei" in classes and "box" in classes:
            self._profundidade_lei = 1
        elif self._profundidade_lei:
            self._profundidade_lei += 1

        if tag == "table":
            self._profundidade_tabela = 1
        elif self._profundidade_tabela:
            self._profundidade_tabela += 1

        for classe, chave in self.BLOCOS.items():
            if classe in classes:
                self.contagem[chave] += 1
                self._registrar_na_secao(chave)

        if tag == "table":
            self.contagem["tabela"] += 1
            self._registrar_na_secao("tabela")

        if tag == "p":
            self._p_atual = []

        if tag == "h2":
            numerado = not self._profundidade_quadro and "sem-numero" not in classes
            self._h2_atual = {
                "id": atributos.get("id", ""),
                "texto": "",
                "numerado": numerado,
            }
            if numerado:
                self.contagem["secao"] += 1
                self.secoes.append({"titulo": "", "palavras": 0})

    def handle_endtag(self, tag):  # noqa: D102
        if self._pilha_ignorar and self._pilha_ignorar[-1] == tag:
            self._pilha_ignorar.pop()
            return

        if tag == "p" and self._p_atual is not None:
            texto = " ".join("".join(self._p_atual).split())
            if texto and not (self._profundidade_lei or self._profundidade_tabela):
                self.paragrafos.append(texto)
            self._p_atual = None

        if tag == "h2" and self._h2_atual is not None:
            self._h2_atual["texto"] = " ".join(self._h2_atual["texto"].split())
            if self._h2_atual["texto"]:
                self.titulos.append(self._h2_atual)
                if self._h2_atual["numerado"] and self.secoes:
                    self.secoes[-1]["titulo"] = self._h2_atual["texto"]
            self._h2_atual = None

        if self._profundidade_quadro:
            self._profundidade_quadro -= 1
        if self._profundidade_lei:
            self._profundidade_lei -= 1
        if self._profundidade_tabela:
            self._profundidade_tabela -= 1

    def handle_data(self, data):  # noqa: D102
        if self._pilha_ignorar:
            return
        self.partes.append(data)
        if not (self._profundidade_lei or self._profundidade_tabela):
            self.partes_autorais.append(data)
        if self._p_atual is not None:
            self._p_atual.append(data)
        if self._h2_atual is not None:
            self._h2_atual["texto"] += data
        if self.secoes and not self._profundidade_quadro:
            self.secoes[-1]["palavras"] += contar_palavras(data)


def analisar_corpo(corpo_html: str) -> dict:
    """Devolve texto puro, contagens, títulos e a estrutura didática do corpo."""
    parser = _ExtratorTexto()
    parser.feed(corpo_html)
    parser.close()
    texto = " ".join(" ".join(parser.partes).split())
    autoral = " ".join(" ".join(parser.partes_autorais).split())
    return {
        "texto": texto,
        "texto_autoral": autoral,
        "palavras": contar_palavras(texto),
        "contagem": parser.contagem,
        "titulos": parser.titulos,
        "secoes": parser.secoes,
        "paragrafos": parser.paragrafos,
    }


# --- Modelo de tempo ------------------------------------------------------
# 170 palavras/min é leitura de estudo densa em pt-BR (não leitura corrida).
PPM = 170
CUSTO = {
    "box": 0.3,
    "tabela": 0.8,
    "pare_responda": 0.5,
    "checkpoint": 0.5,
    "quadro_sintese": 0.8,
    "exemplo": 0.2,
    "passo_a_passo": 0.3,
}
MIN_MINUTOS = 20
MAX_MINUTOS = 45
# Reserva média dos elementos de uma aula bem construída, usada no orçamento de
# palavras. Menos caixas e um único checkpoint = menos paradas.
RESERVA_ELEMENTOS_MIN = 6.0
# Faixa editorial de 350–450 palavras por unidade de conteúdo.
PALAVRAS_POR_UNIDADE = 400


def estimar_minutos(analise: dict) -> dict:
    """Estima os minutos de estudo do conteúdo (sem questões, gabarito ou cards)."""
    leitura = analise["palavras"] / PPM
    extras = sum(analise["contagem"].get(k, 0) * peso for k, peso in CUSTO.items())
    total = leitura + extras
    return {
        "leitura": round(leitura, 1),
        "extras": round(extras, 1),
        "total": round(total, 1),
        "dentro_da_faixa": MIN_MINUTOS <= total <= MAX_MINUTOS,
    }


def palavras_para_minutos(minutos: float) -> int:
    """Quantas palavras de corpo cabem num alvo de minutos, já descontados os elementos."""
    return int(max(0.0, minutos - RESERVA_ELEMENTOS_MIN) * PPM)


# --- Verificação didática -------------------------------------------------

JARGAO_DECORATIVO = (
    "outrossim", "destarte", "conquanto", "insta consignar", "cumpre salientar",
    "cumpre ressaltar", "mister se faz", "urge destacar", "hodiernamente",
    "no bojo", "data venia", "ad argumentandum",
)
# 6 linhas na coluna de leitura de 156 mm, a ~13 palavras por linha —
# a regra do "parágrafo de 3 a 6 linhas".
MAX_PALAVRAS_PARAGRAFO = 85
MAX_PALAVRAS_FRASE = 40
FRASE_MONSTRO = 60
MEDIA_FRASE_ALVO = 24
# Densidade máxima de sinalização: 1 caixa a cada 350 palavras.
MIN_PALAVRAS_POR_CAIXA = 350
MAX_CAIXAS_AULA = 10
MAX_EM_OUTRAS_PALAVRAS = 3

# Palavras funcionais do pt-BR (artigos, preposições, pronomes, conjunções):
# uma janela repetida só interessa se carregar conteúdo além delas.
STOPWORDS_PT = frozenset("""
    a o as os um uma uns umas
    de do da dos das em no na nos nas por pelo pela pelos pelas
    para com sem sob sobre entre até desde ao aos à às
    que se sua seu suas seus ele ela eles elas este esta esse essa
    isso isto aquele aquela qual quem lhe nós
    e ou mas nem pois porque quando como já não
""".split())


def _repeticoes(texto: str, maximo: int = 3) -> list[tuple[str, int]]:
    """Formulações repetidas 3+ vezes no texto autoral, as mais frequentes primeiro.

    Heurística literal: normaliza (minúsculas, sem pontuação) e compara janelas
    deslizantes de 5 palavras com pelo menos 3 fora da lista de stopwords.
    Pega repetição literal ou quase literal; paráfrase fica para o revisor.
    """
    palavras = re.sub(r"[^\w\s]", " ", texto.lower()).split()
    contagem: dict[tuple, int] = {}
    primeira: dict[tuple, int] = {}
    for i in range(len(palavras) - 4):
        janela = tuple(palavras[i:i + 5])
        if sum(1 for p in janela if p not in STOPWORDS_PT) < 3:
            continue
        contagem[janela] = contagem.get(janela, 0) + 1
        primeira.setdefault(janela, i)

    repetidas = {j: n for j, n in contagem.items() if n >= 3}
    # Janelas sobrepostas com a mesma contagem são a mesma repetição vista por
    # recortes diferentes: fundem-se no trecho maior.
    trechos: list[list[int]] = []  # [início, fim, ocorrências]
    for janela in sorted(repetidas, key=lambda j: primeira[j]):
        inicio, n = primeira[janela], repetidas[janela]
        if trechos and trechos[-1][2] == n and inicio <= trechos[-1][1]:
            trechos[-1][1] = max(trechos[-1][1], inicio + 5)
        else:
            trechos.append([inicio, inicio + 5, n])

    trechos.sort(key=lambda t: -t[2])
    return [(" ".join(palavras[ini:fim]), n) for ini, fim, n in trechos[:maximo]]


def revisar_didatica(analise: dict) -> list[str]:
    """Avisos sobre o que costuma travar o leitor. Não bloqueiam a montagem."""
    avisos: list[str] = []

    for i, secao in enumerate(analise.get("secoes") or [], 1):
        rotulo = secao.get("titulo") or f"seção {i}"
        if secao.get("palavras", 0) < 60:
            continue  # seção de abertura ou muito curta: nada a exigir
        if not (secao.get("exemplo") or secao.get("passo_a_passo")):
            avisos.append(f'"{rotulo}" não tem nenhum exemplo concreto — todo conceito '
                          "abstrato precisa de um caso para ancorar")

    longos = [p for p in analise.get("paragrafos") or [] if contar_palavras(p) > MAX_PALAVRAS_PARAGRAFO]
    if longos:
        avisos.append(f"{len(longos)} parágrafo(s) acima de {MAX_PALAVRAS_PARAGRAFO} palavras — "
                      f'quebre em blocos de uma ideia (começa com "{longos[0][:60]}…")')

    autoral = analise.get("texto_autoral") or analise.get("texto", "")
    frases = [f.strip() for f in re.split(r"(?<=[.!?])\s+", autoral) if f.strip()]
    if frases:
        media = sum(contar_palavras(f) for f in frases) / len(frases)
        if media > MEDIA_FRASE_ALVO:
            avisos.append(f"frases com média de {media:.0f} palavras — o alvo é até "
                          f"{MEDIA_FRASE_ALVO}; use ordem direta e corte as intercaladas")
        arrastadas = [f for f in frases if contar_palavras(f) > MAX_PALAVRAS_FRASE]
        if len(arrastadas) > 2:
            avisos.append(f"{len(arrastadas)} frases acima de {MAX_PALAVRAS_FRASE} palavras — "
                          f'a maior começa com "{max(arrastadas, key=contar_palavras)[:60]}…"')
        # Uma única frase-monstro já basta para travar a leitura.
        for f in frases:
            if contar_palavras(f) > FRASE_MONSTRO:
                avisos.append(f"frase de {contar_palavras(f)} palavras — quebre em três ou "
                              f'quatro: "{f[:60]}…"')

    texto_baixo = autoral.lower()
    achados = sorted({j for j in JARGAO_DECORATIVO if j in texto_baixo})
    if achados:
        avisos.append(f"juridiquês decorativo: {', '.join(achados)} — troque por linguagem direta")

    palavras = analise.get("palavras", 0)
    exemplos = analise["contagem"].get("exemplo", 0) + analise["contagem"].get("passo_a_passo", 0)
    if palavras > 1200 and exemplos and palavras / exemplos > 900:
        avisos.append(f"1 exemplo a cada {int(palavras / exemplos)} palavras — pouco para uma "
                      "aula didática (alvo: pelo menos um por seção)")

    caixas = analise["contagem"].get("box", 0)
    if caixas and palavras / caixas < MIN_PALAVRAS_POR_CAIXA:
        avisos.append(f"1 caixa de sinalização a cada {int(palavras / caixas)} palavras — "
                      "densidade alta demais, a sinalização perde efeito "
                      f"(mínimo: {MIN_PALAVRAS_POR_CAIXA})")
    if caixas > MAX_CAIXAS_AULA:
        avisos.append(f"{caixas} caixas de sinalização — o teto é {MAX_CAIXAS_AULA} por aula; "
                      "escolha as que sustentam seção")

    em_outras = analise["contagem"].get("em_outras_palavras", 0)
    if em_outras > MAX_EM_OUTRAS_PALAVRAS:
        avisos.append(f"{em_outras} blocos 'em outras palavras' — o teto é "
                      f"{MAX_EM_OUTRAS_PALAVRAS} por aula; reescreva a prosa em vez "
                      "de duplicá-la")

    checkpoints = analise["contagem"].get("checkpoint", 0)
    if checkpoints > 1:
        avisos.append(f"{checkpoints} checkpoints — o modelo é um único, antes da síntese, "
                      "com uma afirmação por seção")

    for trecho, n in _repeticoes(autoral):
        avisos.append(f'a formulação "…{trecho}…" aparece {n}× — ensine uma vez, '
                      "consolide uma (regra 11)")

    return avisos


# --- E/S ------------------------------------------------------------------


def carregar_json(caminho: Path) -> dict:
    try:
        return json.loads(caminho.read_text(encoding="utf-8"))
    except FileNotFoundError:
        erro(f"arquivo não encontrado: {caminho}")
    except json.JSONDecodeError as e:
        erro(f"JSON inválido em {caminho}: {e}")
    return {}


def erro(mensagem: str) -> None:
    print(f"ERRO: {mensagem}", file=sys.stderr)
    raise SystemExit(1)


def aviso(mensagem: str) -> None:
    print(f"aviso: {mensagem}", file=sys.stderr)
