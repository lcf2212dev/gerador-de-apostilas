#!/usr/bin/env python3
"""ler_grafo.py — o único arquivo desta skill que conhece o formato do grafo.

Três caminhos de leitura, tentados nesta ordem:

1. **motor** — o diretório tem `evidencias.json`: importa
   `.grok/skills/mapear-conteudo/scripts/grafo.py` e usa `calcular()`. É a via rica:
   traz nós, arestas, parâmetros e lacunas em uma passada, exatamente como a skill
   `mapear-conteudo` os calculou.
2. **grafo.md** — parseia o markdown derivado (front-matter, `## 3. Nós`, `## 4. Arestas`,
   e os recortes em `grafo/<disciplina>.md` quando o escopo é grande).
3. **genérico** — último recurso para grafo escrito à mão: mermaid com pesos no rótulo,
   lista aninhada com `[[links]]`, ou tabela com colunas mínimas.

Se o formato do grafo mudar, muda este arquivo — e só ele. `sumario.py` trabalha sobre
as dataclasses abaixo e nunca vê markdown.

Convenções herdadas do motor (`grafo-concurso/1`), respeitadas nos três caminhos:
  - aresta `prerequisito`: **de** é o pré-requisito, **para** é o dependente;
  - aresta `contem`: **de** é o pai, **para** é o filho;
  - `coocorre` e `correlato` são não-dirigidas;
  - `peso` é 0–100 normalizado DENTRO de cada nível — não compare níveis diferentes;
  - `share_pct` é fatia da carga total de questões — esse sim comparável entre quaisquer nós.

Sem dependências externas.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import sys
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

CAMINHO_MOTOR = ".grok/skills/mapear-conteudo/scripts/grafo.py"

TIPOS_ARESTA = {"prerequisito", "correlato", "atualiza", "contem", "coocorre"}

# Sinônimos aceitos ao ler tabelas — cobre o markdown do motor e grafos escritos à mão.
SINONIMOS_NO = {
    "id": ["id", "chave", "slug", "codigo"],
    "rotulo": ["rotulo", "titulo", "nome", "topico", "assunto", "disciplina", "label", "tema"],
    "nivel": ["nivel", "level", "camada"],
    "pai": ["pai", "parent", "parte-de", "parte_de", "grupo"],
    "peso": ["peso", "weight", "prioridade"],
    "classe": ["classe", "class", "faixa"],
    "share_pct": ["share%", "share", "share_pct", "fatia", "fatia%", "percentual", "%"],
    "n_questoes": ["n_q", "n_questoes", "questoes", "qtd", "quantidade", "nq", "incidencia"],
    "edital": ["edital", "no_edital", "cobertura_edital"],
    "tendencia": ["tendencia", "tend", "trend"],
    "confianca": ["confianca", "conf", "confidence"],
    "custo_h": ["custo_h", "custo", "horas", "carga_horaria", "esforco", "h"],
    "roi": ["roi", "retorno"],
    "tipo_cobranca": ["cobranca", "tipo_cobranca", "forma"],
    "origem": ["origem", "fonte_dado"],
    "flags": ["flags", "marcas"],
    "obs": ["obs", "observacao", "nota"],
}

SINONIMOS_ARESTA = {
    "de": ["de", "origem", "from", "source", "prerequisito", "pre"],
    "para": ["para", "destino", "to", "target", "dependente"],
    "tipo": ["tipo", "type", "relacao"],
    "forca": ["forca", "força", "peso", "weight", "strength"],
    "evidencia": ["evidencia", "prova", "nota", "obs"],
}

# Rótulos de aresta de grafos escritos à mão → tipo canônico.
APELIDOS_TIPO = {
    "requer": "prerequisito", "pre": "prerequisito", "pré": "prerequisito",
    "prerequisito": "prerequisito", "pre-requisito": "prerequisito", "depende": "prerequisito",
    "base": "prerequisito", "antes": "prerequisito",
    "contem": "contem", "parte-de": "contem", "parte_de": "contem", "sub": "contem",
    "correlato": "correlato", "relaciona": "correlato", "relacionado": "correlato",
    "coocorre": "coocorre", "co-ocorre": "coocorre", "cai-junto": "coocorre",
    "atualiza": "atualiza", "revoga": "atualiza",
}


class ErroDeLeitura(Exception):
    """O grafo não pôde ser lido em nenhum dos três caminhos."""


@dataclass
class No:
    id: str
    rotulo: str
    nivel: str | None = None
    pai: str | None = None
    peso: float | None = None          # 0–100, normalizado dentro do nível
    classe: str | None = None          # A | B | C | D
    share_pct: float | None = None     # fatia da carga total de questões
    n_questoes: float | None = None
    edital: float | None = None        # 0–1
    tendencia: str | None = None
    confianca: float | None = None     # 0–1
    custo_h: float | None = None
    roi: float | None = None
    tipo_cobranca: list[str] = field(default_factory=list)
    origem: list[str] = field(default_factory=list)
    flags: list[str] = field(default_factory=list)
    obs: str = ""


@dataclass
class Aresta:
    de: str
    para: str
    tipo: str
    forca: float = 1.0
    evidencia: str = ""


@dataclass
class Grafo:
    nos: dict[str, No]
    arestas: list[Aresta]
    meta: dict
    parametros: dict
    lacunas_de_origem: list[dict]
    origem: str          # caminho lido
    sha256: str
    fonte: str           # motor | grafo.md | generico
    avisos: list[str] = field(default_factory=list)

    def filhos_de(self, nid: str) -> list[str]:
        return sorted(n.id for n in self.nos.values() if n.pai == nid)

    def ancestrais_de(self, nid: str) -> list[str]:
        saida, atual, guarda = [], self.nos.get(nid), 0
        while atual and atual.pai and guarda < 64:
            saida.append(atual.pai)
            atual = self.nos.get(atual.pai)
            guarda += 1
        return saida


# --- utilidades -----------------------------------------------------------


def norm(texto) -> str:
    """Sem acento, sem caixa, sem espaço nas pontas — para comparar rótulos."""
    if texto is None:
        return ""
    s = unicodedata.normalize("NFKD", str(texto))
    return "".join(c for c in s if not unicodedata.combining(c)).strip().lower()


def _chave(texto: str) -> str:
    """Normaliza um cabeçalho de coluna para casar com os sinônimos."""
    s = norm(texto).replace(" ", "_").replace("-", "_")
    return re.sub(r"[^a-z0-9_%]", "", s)


def num(valor) -> float | None:
    """Número tolerante a pt-BR. '—', '', 'n/d' viram None."""
    if valor is None:
        return None
    if isinstance(valor, (int, float)):
        return float(valor)
    s = str(valor).strip().replace("%", "")
    if s in {"", "—", "-", "–", "n/d", "nd", "null", "none", "?"}:
        return None
    s = re.sub(r"[^\d,.\-]", "", s)
    if not s or s in {"-", ",", "."}:
        return None
    if "," in s and "." in s:                 # 1.482,50 → milhar + decimal
        s = s.replace(".", "").replace(",", ".")
    elif "," in s:
        inteiro, _, frac = s.partition(",")
        s = f"{inteiro}.{frac}" if len(frac) <= 2 else inteiro + frac
    elif s.count(".") > 1:                    # 1.482.000 → milhar
        s = s.replace(".", "")
    try:
        return float(s)
    except ValueError:
        return None


def _lista(valor) -> list[str]:
    if valor is None:
        return []
    if isinstance(valor, (list, tuple)):
        return [str(v).strip() for v in valor if str(v).strip()]
    s = str(valor).strip()
    if s in {"", "—", "-"}:
        return []
    return [p.strip() for p in re.split(r"[,;/+]| e ", s) if p.strip()]


def _sha256(caminho: Path) -> str:
    return hashlib.sha256(caminho.read_bytes()).hexdigest()


def _tipo_canonico(rotulo: str, padrao: str = "prerequisito") -> str:
    chave = norm(rotulo).replace(" ", "-").strip(".:")
    if chave in TIPOS_ARESTA:
        return chave
    return APELIDOS_TIPO.get(chave, padrao)


# --- front-matter e tabelas ----------------------------------------------


def _valor_yaml(bruto: str):
    """Escalares, listas [a, b] e dicionários {k: v} em uma linha."""
    s = bruto.strip()
    if s.startswith("[") and s.endswith("]"):
        return [p.strip() for p in s[1:-1].split(",") if p.strip()]
    if s.startswith("{") and s.endswith("}"):
        d = {}
        for parte in re.split(r",(?![^{\[]*[}\]])", s[1:-1]):
            if ":" in parte:
                k, _, v = parte.partition(":")
                d[k.strip()] = _valor_yaml(v)
        return d
    n = num(s)
    if n is not None and re.fullmatch(r"[-+]?[\d.,]+%?", s):
        return int(n) if n == int(n) and "." not in s and "," not in s else n
    return s.strip("\"'")


def frontmatter(texto: str) -> dict:
    if not texto.startswith("---"):
        return {}
    fim = texto.find("\n---", 3)
    if fim < 0:
        return {}
    meta = {}
    for linha in texto[3:fim].splitlines():
        if not linha.strip() or linha.lstrip().startswith("#") or ":" not in linha:
            continue
        chave, _, valor = linha.partition(":")
        meta[chave.strip()] = _valor_yaml(valor)
    return meta


def tabelas(texto: str) -> list[list[dict]]:
    """Toda tabela markdown do texto, como lista de dicionários {coluna: célula}."""
    saida, linhas = [], texto.splitlines()
    i = 0
    while i < len(linhas):
        if linhas[i].strip().startswith("|") and i + 1 < len(linhas) \
                and re.fullmatch(r"\|[\s:|-]+\|?", linhas[i + 1].strip()):
            cab = [c.strip() for c in linhas[i].strip().strip("|").split("|")]
            corpo, j = [], i + 2
            while j < len(linhas) and linhas[j].strip().startswith("|"):
                celulas = [c.strip() for c in linhas[j].strip().strip("|").split("|")]
                celulas += [""] * (len(cab) - len(celulas))
                corpo.append(dict(zip(cab, celulas[:len(cab)])))
                j += 1
            if corpo:
                saida.append(corpo)
            i = j
        else:
            i += 1
    return saida


def _mapear(cabecalhos: list[str], sinonimos: dict[str, list[str]]) -> dict[str, str]:
    """{campo canônico: nome da coluna} para as colunas reconhecidas."""
    mapa = {}
    for coluna in cabecalhos:
        c = _chave(coluna)
        for campo, nomes in sinonimos.items():
            if campo in mapa:
                continue
            if c == _chave(campo) or c in {_chave(n) for n in nomes}:
                mapa[campo] = coluna
                break
    return mapa


# --- caminho 1: o motor ---------------------------------------------------


def _achar_motor(inicio: Path) -> Path | None:
    """Sobe do grafo e do próprio script até achar a skill que gera o grafo."""
    daqui = Path(__file__).resolve()
    for base in [inicio, *inicio.parents, *daqui.parents]:
        candidato = base / CAMINHO_MOTOR
        if candidato.is_file():
            return candidato
    irmao = daqui.parents[2] / "mapear-conteudo" / "scripts" / "grafo.py"   # .../skills/
    return irmao if irmao.is_file() else None


def _via_motor(diretorio: Path) -> Grafo:
    motor = _achar_motor(diretorio.resolve())
    if not motor:
        raise ErroDeLeitura("evidencias.json presente, mas grafo.py não foi encontrado")
    spec = importlib.util.spec_from_file_location("motor_grafo", motor)
    mod = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)
        ev = json.loads((diretorio / "evidencias.json").read_text(encoding="utf-8"))
        aj_path = diretorio / "ajustes.json"
        ajustes = json.loads(aj_path.read_text(encoding="utf-8")) if aj_path.is_file() else {}
        derivado = mod.calcular(ev, ajustes)
    except SystemExit as e:                      # o motor aborta com erro() em caso ruim
        raise ErroDeLeitura(f"o motor recusou o evidencias.json ({e})") from e
    except Exception as e:
        raise ErroDeLeitura(f"falha ao rodar o motor: {type(e).__name__}: {e}") from e

    nos = {}
    for n in derivado.get("nos", []):
        nos[n["id"]] = No(
            id=n["id"], rotulo=n.get("rotulo", n["id"]), nivel=n.get("nivel"),
            pai=n.get("pai") or None, peso=num(n.get("peso")), classe=n.get("classe"),
            share_pct=num(n.get("share_pct")), n_questoes=num(n.get("n_questoes")),
            edital=num(n.get("edital")), tendencia=n.get("tendencia"),
            confianca=num(n.get("confianca")), custo_h=num(n.get("custo_h")),
            roi=num(n.get("roi")), tipo_cobranca=_lista(n.get("tipo_cobranca")),
            origem=_lista(n.get("origem")), flags=_lista(n.get("flags")),
            obs=str(n.get("obs") or ""))
    arestas = [Aresta(a["de"], a["para"], a.get("tipo", "prerequisito"),
                      num(a.get("forca")) or 1.0, str(a.get("evidencia") or ""))
               for a in derivado.get("arestas", []) if a.get("de") and a.get("para")]

    esc = derivado.get("escopo", {}) or {}
    meta = {"escopo": esc.get("rotulo"), "slug": esc.get("slug"), "tipo_escopo": esc.get("tipo"),
            "banca_alvo": esc.get("banca_alvo") or [], "orgaos_alvo": esc.get("orgaos_alvo") or [],
            "janela": esc.get("janela"), "ano_ref": derivado.get("ano_ref"),
            "gerado_em": esc.get("gerado_em"), "totais": derivado.get("totais", {}),
            "schema": getattr(mod, "SCHEMA", "grafo-concurso/1")}
    fonte_hash = diretorio / "evidencias.json"
    return Grafo(nos=nos, arestas=arestas, meta=meta,
                 parametros=derivado.get("parametros", {}) or {},
                 lacunas_de_origem=derivado.get("lacunas", []) or [],
                 origem=str(diretorio), sha256=_sha256(fonte_hash), fonte="motor")


# --- caminho 2: o grafo.md renderizado ------------------------------------


def _no_de_linha(linha: dict, mapa: dict) -> No | None:
    pega = lambda campo: linha.get(mapa[campo], "").strip() if campo in mapa else ""
    ident = pega("id")
    rotulo = pega("rotulo")
    if not ident and not rotulo:
        return None
    if not ident:
        ident = re.sub(r"[^a-z0-9]+", "-", norm(rotulo)).strip("-")
    pai = pega("pai")
    return No(
        id=ident, rotulo=rotulo or ident, nivel=pega("nivel") or None,
        pai=None if pai in {"", "—", "-", "–"} else pai,
        peso=num(pega("peso")), classe=(pega("classe") or None),
        share_pct=num(pega("share_pct")), n_questoes=num(pega("n_questoes")),
        edital=num(pega("edital")), tendencia=pega("tendencia") or None,
        confianca=num(pega("confianca")), custo_h=num(pega("custo_h")),
        roi=num(pega("roi")), tipo_cobranca=_lista(pega("tipo_cobranca")),
        origem=_lista(pega("origem")), flags=_lista(pega("flags")), obs=pega("obs"))


def _via_markdown(caminho: Path) -> Grafo:
    texto = caminho.read_text(encoding="utf-8")
    meta = frontmatter(texto)
    avisos: list[str] = []

    fontes = [caminho]
    recorte = caminho.parent / caminho.stem      # grafo.md → grafo/
    if recorte.is_dir():
        fontes += sorted(recorte.glob("*.md"))

    nos: dict[str, No] = {}
    arestas: list[Aresta] = []
    for arquivo in fontes:
        conteudo = texto if arquivo == caminho else arquivo.read_text(encoding="utf-8")
        for tabela in tabelas(conteudo):
            cab = list(tabela[0].keys())
            m_aresta = _mapear(cab, SINONIMOS_ARESTA)
            if "de" in m_aresta and "para" in m_aresta:
                for linha in tabela:
                    de, para = linha[m_aresta["de"]].strip(), linha[m_aresta["para"]].strip()
                    if not de or not para:
                        continue
                    tipo = _tipo_canonico(linha.get(m_aresta.get("tipo", ""), "") or "prerequisito")
                    forca = num(linha.get(m_aresta.get("forca", ""), "")) or 1.0
                    arestas.append(Aresta(de, para, tipo, forca,
                                          linha.get(m_aresta.get("evidencia", ""), "")))
                continue
            m_no = _mapear(cab, SINONIMOS_NO)
            # tabela de nós de verdade tem id e ao menos um sinal quantitativo
            if "id" not in m_no or not ({"peso", "share_pct", "n_questoes", "nivel"} & set(m_no)):
                continue
            for linha in tabela:
                no = _no_de_linha(linha, m_no)
                if not no:
                    continue
                antigo = nos.get(no.id)
                # o recorte por disciplina é mais completo que o agregado do grafo.md
                if antigo is None or (antigo.nivel is None and no.nivel is not None):
                    nos[no.id] = no

    if not nos:
        raise ErroDeLeitura("nenhuma tabela de nós reconhecida no markdown")

    # hierarquia declarada como aresta `contem` vira o campo `pai`
    for a in arestas:
        if a.tipo == "contem" and a.para in nos and not nos[a.para].pai:
            nos[a.para].pai = a.de
    for nid, no in nos.items():
        if no.pai and no.pai not in nos:
            avisos.append(f"{nid}: pai '{no.pai}' não está no grafo — tratado como raiz")
            no.pai = None

    esperado = num(meta.get("nos"))
    if esperado and abs(esperado - len(nos)) > 0.5:
        avisos.append(f"o front-matter declara {int(esperado)} nós e o markdown entregou "
                      f"{len(nos)} — o recorte por disciplina pode estar faltando")

    parametros = meta.get("parametros") if isinstance(meta.get("parametros"), dict) else {}
    return Grafo(nos=nos, arestas=arestas, meta=meta, parametros=parametros or {},
                 lacunas_de_origem=_lacunas_do_markdown(texto), origem=str(caminho),
                 sha256=_sha256(caminho), fonte="grafo.md", avisos=avisos)


def _lacunas_do_markdown(texto: str) -> list[dict]:
    """A seção `## N. Lacunas e ressalvas` do grafo.md — herdada pelo sumário, não descartada."""
    secao = re.search(r"^##\s*\d*\.?\s*Lacunas[^\n]*\n(.*?)(?=^##\s|\Z)", texto, re.S | re.M)
    if not secao:
        return []
    saida = []
    for linha in secao.group(1).splitlines():
        item = re.match(r"^\s*[-*]\s+(.*\S)\s*$", linha)
        if not item:
            continue
        partido = re.match(r"\*\*(.+?)\*\*\s*[—–-]\s*(.*)$", item.group(1))
        saida.append({"o_que": partido.group(1), "impacto": partido.group(2)} if partido
                     else {"o_que": item.group(1), "impacto": ""})
    return saida


# --- caminho 3: genérico (grafo escrito à mão) ----------------------------

RE_MERMAID_NO = re.compile(r"^\s*([A-Za-z0-9_.\-]+)\s*[\[\(\{]+\"?(.+?)\"?[\]\)\}]+\s*$")
RE_MERMAID_ARESTA = re.compile(
    # sólida (-->, ==>), pontilhada (-.->, -.texto.->) ou linha simples (---)
    r"^\s*([A-Za-z0-9_.\-]+)\s*(-{2,}>|={2,}>|-\.[^>|]*->|-{3,})\s*(?:\|([^|]*)\|)?\s*"
    r"([A-Za-z0-9_.\-]+)")
RE_QUESTOES = re.compile(r"(\d[\d.,]*)\s*(?:q\b|quest|questões|questoes)", re.I)
RE_MINUTOS = re.compile(r"(\d[\d.,]*)\s*min", re.I)
RE_HORAS = re.compile(r"(\d[\d.,]*)\s*h\b", re.I)
RE_PESO_BR = re.compile(r"<br\s*/?>\s*(\d[\d.,]*)")


def _enriquecer(no: No, texto: str) -> None:
    if (m := RE_QUESTOES.search(texto)):
        no.n_questoes = num(m.group(1))
    if (m := RE_MINUTOS.search(texto)):
        no.custo_h = (num(m.group(1)) or 0) / 60
    elif (m := RE_HORAS.search(texto)):
        no.custo_h = num(m.group(1))
    if (m := RE_PESO_BR.search(texto)):
        no.peso = num(m.group(1))


def _via_generico(caminho: Path) -> Grafo:
    texto = caminho.read_text(encoding="utf-8")
    meta = frontmatter(texto)
    nos: dict[str, No] = {}
    arestas: list[Aresta] = []

    def registrar(ident: str, rotulo: str | None = None) -> No:
        no = nos.get(ident)
        if no is None:
            no = nos[ident] = No(id=ident, rotulo=rotulo or ident)
        elif rotulo and no.rotulo == no.id:
            no.rotulo = rotulo
        return no

    # -- mermaid
    for bloco in re.findall(r"```mermaid(.*?)```", texto, re.S):
        for linha in bloco.splitlines():
            if (m := RE_MERMAID_ARESTA.match(linha)):
                de, seta, rotulo, para = m.groups()
                padrao = "correlato" if seta.startswith("-.") or seta.startswith("---") \
                    else "prerequisito"
                tipo = _tipo_canonico(rotulo or "", padrao) if rotulo else padrao
                forca = num(rotulo) if rotulo and num(rotulo) is not None else 1.0
                registrar(de), registrar(para)
                arestas.append(Aresta(de, para, tipo, min(forca, 1.0) or 1.0))
            elif (m := RE_MERMAID_NO.match(linha)):
                ident, rotulo = m.group(1), m.group(2)
                if ident in {"graph", "flowchart", "subgraph", "classDef", "class"}:
                    continue
                limpo = re.sub(r"<br\s*/?>.*$", "", rotulo).strip()
                _enriquecer(registrar(ident, limpo), rotulo)

    # -- lista aninhada
    pilha: list[tuple[int, str]] = []
    for linha in texto.splitlines():
        if not (m := re.match(r"^(\s*)[-*+]\s+(.*\S)\s*$", linha)):
            continue
        recuo, corpo = len(m.group(1).expandtabs(4)), m.group(2)
        rel = re.match(r"^(requer|pré-requisito|pre-requisito|depende de|destrava|"
                       r"relaciona|cai junto com)\s*:\s*(.+)$", corpo, re.I)
        if rel and pilha:
            alvo = pilha[-1][1]
            verbo = norm(rel.group(1))
            for parte in re.split(r"[,;]| e ", rel.group(2)):
                nome = parte.strip().strip("[]").strip()
                if not nome or norm(nome) in {"nada", "nenhum", "—", "-"}:
                    continue
                ident = re.sub(r"[^a-z0-9]+", "-", norm(nome)).strip("-")
                registrar(ident, nome)
                if verbo.startswith("destrava"):
                    arestas.append(Aresta(alvo, ident, "prerequisito", 1.0))
                elif verbo.startswith(("relaciona", "cai")):
                    arestas.append(Aresta(alvo, ident, "correlato", 1.0))
                else:
                    arestas.append(Aresta(ident, alvo, "prerequisito", 1.0))
            continue
        rotulo = re.sub(r"\[\[(.+?)\]\]", r"\1", corpo)
        rotulo = re.sub(r"\((?:[^()]*)\)|—.*$|::.*$", "", rotulo).strip(" .:-")
        if not rotulo:
            continue
        ident = re.sub(r"[^a-z0-9]+", "-", norm(rotulo)).strip("-")
        if not ident:
            continue
        no = registrar(ident, rotulo)
        _enriquecer(no, corpo)
        while pilha and pilha[-1][0] >= recuo:
            pilha.pop()
        if pilha:
            no.pai = pilha[-1][1]
            arestas.append(Aresta(pilha[-1][1], ident, "contem", 1.0))
        pilha.append((recuo, ident))

    if not nos:
        raise ErroDeLeitura(
            "não reconheci nenhum grafo neste arquivo. Formatos aceitos: o `grafo.md` da skill "
            "mapear-conteudo, um diretório com `evidencias.json`, um bloco ```mermaid``` ou uma "
            "lista aninhada de tópicos")
    return Grafo(nos=nos, arestas=arestas, meta=meta, parametros={}, lacunas_de_origem=[],
                 origem=str(caminho), sha256=_sha256(caminho), fonte="generico",
                 avisos=["grafo lido em modo genérico: pesos, edital, confiança e custo podem "
                         "estar ausentes"])


# --- despacho -------------------------------------------------------------


def carregar(alvo) -> Grafo:
    """Aceita: diretório do grafo, slug (`grafos/<slug>`), `grafo.md` ou `evidencias.json`."""
    caminho = Path(alvo).expanduser()
    if not caminho.exists() and "/" not in str(alvo):
        for base in [Path.cwd(), *Path.cwd().parents, Path(__file__).resolve().parents[4]]:
            candidato = base / "grafos" / str(alvo)
            if candidato.exists():
                caminho = candidato
                break
    if not caminho.exists():
        raise ErroDeLeitura(f"não encontrei o grafo: {alvo}")

    if caminho.is_file() and caminho.name == "evidencias.json":
        caminho = caminho.parent
    if caminho.is_dir():
        if (caminho / "evidencias.json").is_file():
            try:
                return _via_motor(caminho)
            except ErroDeLeitura as e:
                if (caminho / "grafo.md").is_file():
                    g = _via_markdown(caminho / "grafo.md")
                    g.avisos.append(f"motor indisponível ({e}) — li o grafo.md renderizado")
                    return g
                raise
        for nome in ("grafo.md", "GRAFO.md", "index.md"):
            if (caminho / nome).is_file():
                return carregar(caminho / nome)
        raise ErroDeLeitura(f"{caminho} não tem evidencias.json nem grafo.md")

    if (caminho.parent / "evidencias.json").is_file():
        try:
            return _via_motor(caminho.parent)
        except ErroDeLeitura:
            pass
    try:
        return _via_markdown(caminho)
    except ErroDeLeitura:
        return _via_generico(caminho)


def cobertura_de_campos(g: Grafo) -> dict[str, float]:
    """Fração dos nós que traz cada campo — insumo do relatório de lacunas."""
    total = len(g.nos) or 1
    campos = ["peso", "classe", "share_pct", "n_questoes", "edital", "confianca", "custo_h",
              "nivel", "tendencia"]
    return {c: round(sum(1 for n in g.nos.values() if getattr(n, c) not in (None, "")) / total, 4)
            for c in campos}


if __name__ == "__main__":                       # diagnóstico rápido: ler_grafo.py <alvo>
    if len(sys.argv) < 2:
        print(__doc__)
        raise SystemExit(0)
    grafo = carregar(sys.argv[1])
    print(f"fonte={grafo.fonte} nós={len(grafo.nos)} arestas={len(grafo.arestas)} "
          f"sha256={grafo.sha256[:12]}")
    print("campos:", json.dumps(cobertura_de_campos(grafo), ensure_ascii=False))
    for aviso in grafo.avisos:
        print("aviso:", aviso)
