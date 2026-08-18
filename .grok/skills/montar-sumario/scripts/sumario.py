#!/usr/bin/env python3
"""sumario.py — motor determinístico do sumário de estudo priorizado.

Divisão de trabalho desta skill: **o script calcula, o modelo redige.** Tudo que é
número — importância, ordem, cobertura, horas — sai daqui. O `sumario.md` é escrito
a partir do `plano.json` que este script emite, e `conferir` reprova qualquer número
que apareça no markdown sem existir no plano.

O grafo já entrega peso, classe, share, edital, confiança, tendência e custo (é a skill
`mapear-conteudo` que os calcula, a partir de provas e editais reais). O que esta skill
acrescenta é o que falta para virar um plano de estudo:

  1. **centralidade "destrava"** — PageRank sobre os pré-requisitos invertidos: quanto
     valor do resto do edital este tópico libera. O grafo não calcula isso.
  2. **importância 1–10** — a escada legível, ancorada no valor composto.
  3. **fila** — ordem topológica desempatada por ROI, com bônus de coesão para o que
     cai junto.
  4. **módulos, cobertura acumulada e grade de aulas.**

Determinismo: mesmo grafo + mesmos parâmetros = mesmo plano. Não há relógio nem sorteio
no cálculo; `gerado_em` é o único campo que muda, e sai de `--data` quando informado.

Comandos:
    inspecionar <alvo>                     diagnóstico do grafo antes de gastar trabalho
    priorizar   <alvo> --assunto "..."     emite o plano.json
    conferir --plano p.json --grade g.json [--sumario s.md]

Sem dependências externas.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import difflib
import json
import math
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ler_grafo import (Grafo, No, ErroDeLeitura, carregar, cobertura_de_campos,  # noqa: E402
                       norm)

VERSAO = "1.0.0"

PADROES = {
    "beta_centralidade": 0.35,   # quanto do valor vem de "destrava" e não de "cai"
    "damping": 0.85,             # amortecimento do PageRank
    "gama": 1.00,                # curvatura da escada 1–10 (1.0 = linear no valor relativo)
    "coesao": 0.15,              # bônus de fila para o que cai junto com o item anterior
    "expoente_esforco": 0.50,    # ROI da fila = valor / horas^k; k<1 impede que o tópico
                                 # curto e irrelevante fure a fila só por ser barato
    "minutos_aula": 30,          # alvo por aula; a skill `apostila` trabalha em 20–45
    "minutos_min": 20,
    "minutos_max": 45,
    "cortes": [0.50, 0.70, 0.90],
    "w_incidencia": 0.65,        # usados só quando o `peso` do grafo não é comparável
    "w_edital": 0.35,
    "limiar_confianca_baixa": 0.30,
    "max_projecao_arestas": 400,  # acima disto, a aresta entre ramos vira representante
}

# A nota é o valor do item medido contra o item mais valioso DO RECORTE, em décimos.
# Escala relativa e declarada: 7/10 significa "vale 70% do que vale o topo desta lista".
ANCORAS = [
    (10, "O topo do recorte — núcleo absoluto, cai em praticamente toda prova"),
    (9, "90% do valor do topo — alta incidência ou destrava boa parte do edital"),
    (8, "80% do valor do topo — alta incidência ou destrava boa parte do edital"),
    (7, "70% do valor do topo — cobrança regular e previsível"),
    (6, "60% do valor do topo — cobrança regular e previsível"),
    (5, "metade do valor do topo — aparece de vez em quando, vale uma passada"),
    (4, "40% do valor do topo — aparece de vez em quando, vale uma passada"),
    (3, "30% do valor do topo — raro; só depois que o núcleo estiver dominado"),
    (2, "20% do valor do topo — raro; só depois que o núcleo estiver dominado"),
    (1, "10% ou menos do topo — marginal, ou fora do edital-alvo"),
]

PALAVRAS_TUDO = {"tudo", "todos", "todo o edital", "edital", "edital inteiro", "geral",
                 "completo", "o escopo", "escopo"}


def erro(msg: str) -> None:
    print(f"ERRO: {msg}", file=sys.stderr)
    raise SystemExit(1)


# --- recorte --------------------------------------------------------------


def resolver_assunto(g: Grafo, assunto: str) -> str | None:
    """Devolve o id do nó-raiz do recorte, ou None para 'o grafo inteiro'."""
    alvo = norm(assunto)
    if assunto in g.nos:
        return assunto
    exatos = [n.id for n in g.nos.values() if norm(n.rotulo) == alvo]
    if len(exatos) == 1:
        return exatos[0]
    # o escopo do grafo é o grafo inteiro — mas só depois de tentar casar com um nó,
    # senão o nó-raiz vira o único módulo e o sumário perde a divisão em módulos
    if alvo in PALAVRAS_TUDO or alvo == norm(g.meta.get("escopo")) or alvo == norm(g.meta.get("slug")):
        raizes = [n.id for n in g.nos.values() if not n.pai]
        return raizes[0] if len(raizes) == 1 else None
    if len(exatos) > 1:
        erro("assunto ambíguo — mais de um nó com esse rótulo: "
             + ", ".join(f"{i} ({g.nos[i].nivel or '?'})" for i in sorted(exatos)))
    contidos = [n.id for n in g.nos.values() if alvo and alvo in norm(n.rotulo)]
    if len(contidos) == 1:
        return contidos[0]
    rotulos = {n.id: norm(n.rotulo) for n in g.nos.values()}
    parecidos = sorted(
        ((difflib.SequenceMatcher(None, alvo, r).ratio(), i) for i, r in rotulos.items()),
        reverse=True)
    if parecidos and parecidos[0][0] >= 0.82 and (
            len(parecidos) == 1 or parecidos[0][0] - parecidos[1][0] > 0.05):
        return parecidos[0][1]
    sugestao = ", ".join(f"{i} ({g.nos[i].rotulo})" for _, i in parecidos[:8])
    if contidos:
        sugestao = ", ".join(f"{i} ({g.nos[i].rotulo})" for i in sorted(contidos)[:8])
    erro(f"não encontrei o assunto '{assunto}' no grafo. Candidatos: {sugestao}")
    return None


def descendentes(g: Grafo, raiz: str) -> set[str]:
    saida, fila = {raiz}, [raiz]
    while fila:
        for filho in g.filhos_de(fila.pop()):
            if filho not in saida:
                saida.add(filho)
                fila.append(filho)
    return saida


def montar_recorte(g: Grafo, raiz: str | None, importar_prereq: bool) -> tuple[set[str], set[str]]:
    """(ids no recorte, ids importados por serem pré-requisito de fora do assunto)."""
    dentro = set(g.nos) if raiz is None else descendentes(g, raiz)
    importados: set[str] = set()
    if raiz is None or not importar_prereq:
        return dentro, importados
    pre_de = defaultdict(set)
    for a in g.arestas:
        if a.tipo == "prerequisito":
            pre_de[a.para].add(a.de)
    fronteira = list(dentro)
    while fronteira:
        atual = fronteira.pop()
        for pre in sorted(pre_de.get(atual, ())):
            if pre in dentro or pre not in g.nos:
                continue
            # traz o ramo inteiro do pré-requisito: estudar um tema é estudar o conteúdo dele
            ramo = descendentes(g, pre)
            novos = ramo - dentro
            dentro |= novos
            importados |= novos
            fronteira.extend(novos)
    return dentro, importados


# --- valor ----------------------------------------------------------------


def _normalizar(valores: dict[str, float]) -> dict[str, float]:
    teto = max(valores.values(), default=0.0)
    if teto <= 0:
        return {k: 0.0 for k in valores}
    return {k: v / teto for k, v in valores.items()}


def base_de_valor(g: Grafo, itens: list[No], par: dict) -> tuple[dict[str, float], str, list[str]]:
    """O quanto cada item vale por si — antes da centralidade.

    Preferência pelo `peso` do grafo, que já embute incidência com decaimento, banca,
    edital e tendência. Mas `peso` é normalizado DENTRO de cada nível: só é comparável
    se todos os itens estiverem no mesmo nível. Quando não estão, cai para
    share de questões + edital, ambos comparáveis entre quaisquer nós.
    """
    avisos: list[str] = []
    niveis = {n.nivel for n in itens if n.nivel}
    tem_peso = all(n.peso is not None for n in itens)
    if tem_peso and len(niveis) <= 1:
        return ({n.id: (n.peso or 0.0) / 100 for n in itens}, "peso", avisos)

    if tem_peso and len(niveis) > 1:
        avisos.append(f"os itens estão em {len(niveis)} níveis diferentes "
                      f"({', '.join(sorted(str(x) for x in niveis))}) e o `peso` do grafo é "
                      "normalizado por nível — usei share de questões + edital no lugar")
    tem_share = any(n.share_pct for n in itens)
    tem_q = any(n.n_questoes for n in itens)
    if not tem_share and not tem_q and not any(n.edital for n in itens):
        avisos.append("o grafo não traz peso, share, questões nem edital — todos os itens "
                      "entraram com o mesmo valor; a ordem é só topológica")
        return ({n.id: 1.0 for n in itens}, "uniforme", avisos)

    bruto = {n.id: (n.share_pct if tem_share else (n.n_questoes or 0.0)) or 0.0 for n in itens}
    incidencia = _normalizar(bruto)
    w_i = float(par.get("w_incidencia", PADROES["w_incidencia"]))
    w_e = float(par.get("w_edital", PADROES["w_edital"]))
    if not any(n.edital for n in itens):
        avisos.append("nenhum item traz o sinal `edital` — o valor saiu só da incidência")
        w_i, w_e = 1.0, 0.0
    base = {n.id: w_i * incidencia[n.id] + w_e * (n.edital or 0.0) for n in itens}
    return base, ("share+edital" if tem_share else "questoes+edital"), avisos


def centralidade(g: Grafo, recorte: set[str], itens: list[No], base: dict[str, float],
                 par: dict) -> tuple[dict[str, float], bool]:
    """PageRank sobre os pré-requisitos invertidos: quanto valor o item destrava.

    A aresta `prerequisito` vai do pré-requisito (de) para o dependente (para). No
    PageRank a massa precisa andar no sentido oposto — do dependente para aquilo de que
    ele depende — então a aresta do passeio é `para → de`.
    """
    arcos = [(a.para, a.de, a.forca) for a in g.arestas
             if a.tipo == "prerequisito" and a.de in recorte and a.para in recorte]
    if not arcos:
        return ({n.id: base.get(n.id, 0.0) for n in itens}, False)

    # teleporte proporcional ao valor: nó interno herda a soma das bases das suas folhas
    ids_itens = {n.id for n in itens}
    folhas_de: dict[str, list[str]] = {}
    for nid in recorte:
        folhas = [f for f in descendentes(g, nid) if f in ids_itens] if nid not in ids_itens \
            else [nid]
        folhas_de[nid] = folhas or [nid]
    t = {nid: sum(base.get(f, 0.0) for f in folhas_de[nid]) for nid in recorte}
    soma_t = sum(t.values())
    t = {k: (v / soma_t if soma_t > 0 else 1 / len(recorte)) for k, v in t.items()}

    saidas = defaultdict(list)
    for de, para, forca in arcos:
        saidas[de].append((para, max(forca, 1e-6)))
    d = float(par.get("damping", PADROES["damping"]))
    r = dict(t)
    for _ in range(200):
        novo = {k: (1 - d) * t[k] for k in recorte}
        vazado = 0.0
        for nid in recorte:
            destinos = saidas.get(nid)
            if not destinos:
                vazado += r[nid]
                continue
            total = sum(f for _, f in destinos)
            for destino, forca in destinos:
                novo[destino] += d * r[nid] * (forca / total)
        for k in recorte:                       # nó sem saída devolve massa ao teleporte
            novo[k] += d * vazado * t[k]
        delta = sum(abs(novo[k] - r[k]) for k in recorte)
        r = novo
        if delta < 1e-12:
            break

    # o item herda a centralidade dos ancestrais, dividida entre as folhas do ramo
    bruto = {}
    for n in itens:
        valor = r.get(n.id, 0.0)
        for anc in g.ancestrais_de(n.id):
            if anc in recorte:
                valor += r.get(anc, 0.0) / max(len(folhas_de.get(anc, [n.id])), 1)
        bruto[n.id] = valor
    return _normalizar(bruto), True


def escada(valor_norm: float, gama: float) -> int:
    """1–10: o valor do item em décimos do valor do item mais forte do recorte.

    Com `gama` = 1 a leitura é direta — 7/10 é "vale 70% do topo". Valores menores que 1
    espalham a base (mais itens em notas altas); maiores que 1 endurecem o topo.
    """
    return max(1, min(10, round(10 * (max(valor_norm, 0.0) ** gama))))


# --- esforço, fila, módulos ----------------------------------------------


def minutos_do_item(n: No, base_n: float, par: dict) -> tuple[int, bool]:
    if n.custo_h and n.custo_h > 0:
        return max(int(round(n.custo_h * 60)), 5), False
    est = 30 + 90 * base_n                      # 30 min no rodapé, 2 h no topo
    return int(min(240, max(30, 15 * round(est / 15)))), True


def fatiar_em_aulas(minutos: int, par: dict) -> list[int]:
    alvo = int(par.get("minutos_aula", PADROES["minutos_aula"]))
    teto = int(par.get("minutos_max", PADROES["minutos_max"]))
    if minutos <= teto:
        return [max(minutos, int(par.get("minutos_min", PADROES["minutos_min"])))]
    n = math.ceil(minutos / alvo)
    fatia = minutos / n
    return [int(round(fatia))] * n


def dependencias_entre_itens(g: Grafo, recorte: set[str], itens: list[No],
                             valor: dict[str, float], par: dict) -> tuple[dict[str, set[str]], list[str]]:
    """Projeta as arestas `prerequisito` do grafo para o nível dos itens."""
    avisos: list[str] = []
    ids = {n.id for n in itens}
    def folhas(nid: str) -> list[str]:
        if nid in ids:
            return [nid]
        return sorted(f for f in descendentes(g, nid) if f in ids)

    dep: dict[str, set[str]] = {n.id: set() for n in itens}
    teto = int(par.get("max_projecao_arestas", PADROES["max_projecao_arestas"]))
    for a in g.arestas:
        if a.tipo != "prerequisito" or a.de not in recorte or a.para not in recorte:
            continue
        origem, destino = folhas(a.de), folhas(a.para)
        if not origem or not destino:
            continue
        if len(origem) * len(destino) > teto:   # ramo × ramo: liga ao representante
            origem = [max(origem, key=lambda i: (valor.get(i, 0.0), i))]
            avisos.append(f"aresta {a.de} → {a.para} liga dois ramos grandes; "
                          f"amarrei apenas '{origem[0]}' como pré-requisito")
        for d in destino:
            for o in origem:
                if o != d:
                    dep[d].add(o)
    return dep, avisos


def afinidade(g: Grafo, recorte: set[str]) -> dict[tuple[str, str], float]:
    """Força de 'cai junto' — usada só para desempatar a fila, nunca no valor."""
    pares: dict[tuple[str, str], float] = {}
    for a in g.arestas:
        if a.tipo not in {"coocorre", "correlato"} or a.de not in recorte or a.para not in recorte:
            continue
        for chave in ((a.de, a.para), (a.para, a.de)):
            pares[chave] = max(pares.get(chave, 0.0), min(a.forca, 1.0))
    return pares


def montar_fila(g: Grafo, itens: list[No], dep: dict[str, set[str]], valor: dict[str, float],
                horas: dict[str, float], recorte: set[str], par: dict) -> tuple[list[str], list[list[str]]]:
    """Kahn com desempate por ROI e bônus de coesão. Determinístico."""
    coesao = float(par.get("coesao", PADROES["coesao"]))
    k = float(par.get("expoente_esforco", PADROES["expoente_esforco"]))
    afins = afinidade(g, recorte)
    pai_de = {n.id: n.pai for n in itens}
    pendente = {i: set(d) for i, d in dep.items()}
    fila, ciclos, anterior = [], [], None

    def chave(i: str) -> tuple:
        roi = valor.get(i, 0.0) / max(horas.get(i, 0.5), 0.25) ** k
        bonus = 0.0
        if anterior:
            bonus = afins.get((anterior, i), 0.0)
            if not bonus and pai_de.get(i) and pai_de.get(i) == pai_de.get(anterior):
                bonus = 0.5
        return (-roi * (1 + coesao * bonus), -valor.get(i, 0.0), i)

    restantes = {n.id for n in itens}
    while restantes:
        prontos = [i for i in restantes if not pendente[i]]
        if not prontos:                          # ciclo: quebra pelo de maior valor
            travados = sorted(restantes, key=lambda i: (-valor.get(i, 0.0), i))
            ciclos.append(travados[:12])
            prontos = [travados[0]]
            pendente[travados[0]] = set()
        escolhido = min(prontos, key=chave)
        fila.append(escolhido)
        restantes.discard(escolhido)
        anterior = escolhido
        for i in restantes:
            pendente[i].discard(escolhido)
    return fila, ciclos


MODULO_BASE = "__base__"


def agrupar_em_modulos(g: Grafo, raiz: str | None, itens: list[No], fila: list[str],
                       peso_modulo: dict[str, float],
                       importados: set[str]) -> tuple[list[dict], dict[str, str]]:
    """Módulo = o ancestral logo abaixo da raiz do recorte (ou o topo, se raiz é None).

    Pré-requisito importado de fora do assunto não pertence a nenhum módulo do assunto:
    todos vão para o módulo 0, a base que precisa vir antes.
    """
    referencia = raiz
    if referencia is None:                        # grafo inteiro: usa a raiz única, se houver
        raizes = [n.id for n in g.nos.values() if not n.pai]
        referencia = raizes[0] if len(raizes) == 1 else None

    def modulo_de(nid: str) -> str:
        if nid in importados:
            return MODULO_BASE
        cadeia = [nid] + g.ancestrais_de(nid)     # do item até a raiz do grafo
        if referencia is not None and referencia in cadeia:
            corte = cadeia.index(referencia)
            # corte == 1 é filho direto da raiz: o módulo é a raiz, não o próprio item
            return cadeia[corte - 1] if corte > 1 else referencia
        return cadeia[-1] if cadeia else nid

    dono = {n.id: modulo_de(n.id) for n in itens}
    grupos = defaultdict(list)
    for nid in fila:
        grupos[dono[nid]].append(nid)
    ordenados = sorted(grupos, key=lambda m: (m != MODULO_BASE,
                                              -sum(peso_modulo.get(i, 0.0) for i in grupos[m]), m))
    modulos, numero = [], {}
    primeiro = 0 if MODULO_BASE in grupos else 1
    for k, mid in enumerate(ordenados, primeiro):
        for j, nid in enumerate(grupos[mid], 1):
            numero[nid] = f"{k}.{j}"
        no = g.nos.get(mid)
        modulos.append({"num": k, "id": mid,
                        "rotulo": "Base — pré-requisitos de fora do assunto"
                                  if mid == MODULO_BASE else (no.rotulo if no else mid),
                        "nivel": None if mid == MODULO_BASE else (no.nivel if no else None),
                        "itens": grupos[mid]})
    return modulos, numero


# --- o comando priorizar --------------------------------------------------


def priorizar(g: Grafo, assunto: str, par: dict, importar_prereq: bool = True) -> dict:
    raiz = resolver_assunto(g, assunto)
    recorte, importados = montar_recorte(g, raiz, importar_prereq)
    if not recorte:
        erro("o recorte ficou vazio")

    com_filho = {g.nos[i].pai for i in recorte if g.nos[i].pai in recorte}
    itens = sorted((g.nos[i] for i in recorte if i not in com_filho), key=lambda n: n.id)
    if not itens:
        erro("nenhuma folha no recorte — o grafo tem hierarquia circular?")

    parametros = {**PADROES, **{k: v for k, v in (g.parametros or {}).items() if k in PADROES}, **par}
    base, modo_base, avisos = base_de_valor(g, itens, parametros)
    base_n = _normalizar(base)
    centro, tem_prereq = centralidade(g, recorte, itens, base_n, parametros)
    if not tem_prereq:
        avisos.append("o grafo não declara pré-requisitos: a centralidade foi desligada e a "
                      "fila saiu só por ROI")

    beta = float(parametros["beta_centralidade"]) if tem_prereq else 0.0
    valor = _normalizar({n.id: (1 - beta) * base_n[n.id] + beta * centro.get(n.id, 0.0)
                         for n in itens})
    gama = float(parametros["gama"])
    nota = {n.id: escada(valor[n.id], gama) for n in itens}

    minutos, estimado = {}, {}
    for n in itens:
        m, est = minutos_do_item(n, base_n[n.id], parametros)
        minutos[n.id], estimado[n.id] = m, est
    horas = {i: m / 60 for i, m in minutos.items()}

    dep, avisos_dep = dependencias_entre_itens(g, recorte, itens, valor, parametros)
    avisos += avisos_dep
    fila, ciclos = montar_fila(g, itens, dep, valor, horas, recorte, parametros)

    # o share do grafo é fatia do escopo inteiro; dentro de um recorte ele é renormalizado,
    # senão "cobre 70% das questões" viraria uma promessa sobre um edital que não é o pedido
    total_share = sum((n.share_pct or 0.0) for n in itens)
    total_q = sum((n.n_questoes or 0.0) for n in itens)
    def share_de(n: No) -> float:
        if n.share_pct is not None and total_share:
            return n.share_pct / total_share
        if total_q:
            return (n.n_questoes or 0.0) / total_q
        return 0.0

    peso_modulo = {n.id: (share_de(n) or valor[n.id]) for n in itens}
    modulos, numero = agrupar_em_modulos(g, raiz, itens, fila, peso_modulo, importados)

    por_id = {n.id: n for n in itens}
    destrava = defaultdict(list)
    for alvo, fontes in dep.items():
        for f in fontes:
            destrava[f].append(alvo)

    saida_itens = []
    for posicao, nid in enumerate(fila, 1):
        n = por_id[nid]
        marcas = list(n.flags)
        if nid in importados:
            marcas.append("importado")
        if estimado[nid]:
            marcas.append("custo-estimado")
        if n.confianca is not None and n.confianca < parametros["limiar_confianca_baixa"]:
            marcas.append("confianca-baixa")
        fatias = fatiar_em_aulas(minutos[nid], parametros)
        saida_itens.append({
            "num": numero[nid], "seq": posicao, "id": nid, "rotulo": n.rotulo,
            "nivel": n.nivel, "modulo": next(m["num"] for m in modulos if nid in m["itens"]),
            "importancia": nota[nid],
            "valor": round(valor[nid], 6),
            "componentes": {"base": round(base_n[nid], 6),
                            "centralidade": round(centro.get(nid, 0.0), 6),
                            "peso_grafo": n.peso, "share_pct": n.share_pct,
                            "edital": n.edital, "tendencia": n.tendencia,
                            "confianca": n.confianca},
            "classe_grafo": n.classe,
            "n_questoes": n.n_questoes,
            "share": round(share_de(n), 6),
            "share_do_grafo": round((n.share_pct or 0.0) / 100, 6) if n.share_pct else None,
            "minutos": minutos[nid], "horas": round(horas[nid], 3),
            "aulas": len(fatias), "minutos_por_aula": fatias,
            "roi": round(valor[nid] / max(horas[nid], 0.25), 6),
            "requer": sorted(dep.get(nid, ())),
            "destrava": sorted(destrava.get(nid, ())),
            "tipo_cobranca": n.tipo_cobranca, "marcas": marcas, "obs": n.obs,
        })

    acumulado, curva, marcos = 0.0, [], {}
    cortes = list(parametros["cortes"])
    for it in saida_itens:
        acumulado += it["share"]
        curva.append({"seq": it["seq"], "num": it["num"], "acumulado": round(acumulado, 6),
                      "restante": round(max(0.0, 1 - acumulado), 6)})
        for c in cortes:
            if c not in marcos and acumulado >= c:
                marcos[c] = it["seq"]

    campos = cobertura_de_campos(g)
    lacunas = {
        "sinais_desligados": ([] if tem_prereq else ["centralidade"])
                             + ([] if any(n.edital for n in itens) else ["edital"])
                             + ([] if any(n.confianca for n in itens) else ["confianca"]),
        "sem_incidencia": sorted(n.id for n in itens if not n.n_questoes and not n.share_pct),
        "custo_estimado": sorted(i for i, e in estimado.items() if e),
        "confianca_baixa": sorted(n.id for n in itens if n.confianca is not None
                                  and n.confianca < parametros["limiar_confianca_baixa"]),
        "sem_prerequisito_declarado": sorted(n.id for n in itens if not dep.get(n.id)
                                             and not destrava.get(n.id)),
        "ciclos": ciclos,
        "importados": sorted(importados & {n.id for n in itens}),
        "share_nao_coberto": round(max(0.0, 1 - acumulado), 6),
        "cobertura_de_campos": campos,
        "do_grafo": g.lacunas_de_origem,
        "avisos_de_leitura": g.avisos,
        "avisos_do_calculo": avisos,
    }

    return {
        "versao_skill": VERSAO,
        "gerado_em": par.get("data") or _dt.date.today().isoformat(),
        "grafo": {"origem": g.origem, "sha256": g.sha256, "fonte": g.fonte,
                  "escopo": g.meta.get("escopo"), "slug": g.meta.get("slug"),
                  "banca_alvo": g.meta.get("banca_alvo") or [],
                  "janela": g.meta.get("janela"), "ano_ref": g.meta.get("ano_ref"),
                  "nos": len(g.nos), "arestas": len(g.arestas)},
        "assunto": {"pedido": assunto, "raiz": raiz,
                    "rotulo": g.nos[raiz].rotulo if raiz else (g.meta.get("escopo") or "todo o grafo")},
        "parametros": {**{k: parametros[k] for k in PADROES}, "base_de_valor": modo_base,
                       "beta_aplicado": beta, "importou_prerequisitos": importar_prereq},
        "totais": {
            "nos_no_recorte": len(recorte), "itens": len(itens),
            "questoes": round(total_q, 2) or None,
            "share_do_grafo": round(total_share / 100, 6) if total_share else None,
            "minutos": sum(minutos.values()), "horas": round(sum(horas.values()), 1),
            "aulas": sum(i["aulas"] for i in saida_itens),
            "importancia_media": round(sum(nota.values()) / len(nota), 2),
        },
        "escada": [{"nota": n, "significa": s} for n, s in ANCORAS],
        "modulos": [{**m, "importancia_media": round(
            sum(nota[i] for i in m["itens"]) / len(m["itens"]), 2)} for m in modulos],
        "itens": saida_itens,
        "fila": [i["num"] for i in saida_itens],
        "cobertura": {"curva": curva,
                      "marcos": {f"{int(c*100)}%": marcos.get(c) for c in cortes}},
        "lacunas": lacunas,
    }


# --- o comando inspecionar ------------------------------------------------


def cmd_inspecionar(args) -> None:
    try:
        g = carregar(args.alvo)
    except ErroDeLeitura as e:
        erro(str(e))
    print(f"{g.meta.get('escopo') or '(sem escopo declarado)'}  ·  lido via {g.fonte}")
    print(f"  origem ............. {g.origem}")
    print(f"  sha256 ............. {g.sha256[:16]}")
    if g.meta.get("janela"):
        print(f"  janela ............. {g.meta.get('janela')}  (ano_ref {g.meta.get('ano_ref')})")
    if g.meta.get("banca_alvo"):
        print(f"  banca-alvo ......... {', '.join(g.meta['banca_alvo'])}")
    com_filho = {n.pai for n in g.nos.values() if n.pai}
    folhas = [n for n in g.nos.values() if n.id not in com_filho]
    print(f"  nós ................ {len(g.nos)} ({len(folhas)} folhas)")
    tipos = defaultdict(int)
    for a in g.arestas:
        tipos[a.tipo] += 1
    print(f"  arestas ............ {len(g.arestas)}"
          + (f"  ({', '.join(f'{t}: {c}' for t, c in sorted(tipos.items()))})" if tipos else ""))
    print("  campos por nó:")
    for campo, fracao in cobertura_de_campos(g).items():
        barra = "▓" * round(fracao * 20) + "░" * (20 - round(fracao * 20))
        print(f"    {campo:<12} {barra} {fracao*100:5.1f}%")
    raizes = sorted((n for n in g.nos.values() if not n.pai), key=lambda n: n.id)
    print(f"  raízes ............. {', '.join(f'{n.id} ({n.rotulo})' for n in raizes[:12])}"
          + (" …" if len(raizes) > 12 else ""))
    niveis = sorted({n.nivel for n in folhas if n.nivel})
    if len(niveis) > 1:
        print(f"  ATENÇÃO: folhas em {len(niveis)} níveis ({', '.join(niveis)}) — o `peso` do "
              "grafo não é comparável entre elas; o valor sairá de share+edital")
    for aviso in g.avisos:
        print(f"  aviso .............. {aviso}")
    for l in g.lacunas_de_origem:
        print(f"  lacuna do grafo .... {l.get('o_que', l)}")


# --- o comando conferir ---------------------------------------------------

# o lookbehind evita ler "4/10" dentro de uma média escrita como "5,4/10"
RE_NOTA = re.compile(r"(?<![\d,.])(\d{1,2})\s*/\s*10\b")
RE_PCT = re.compile(r"(\d{1,3}(?:[.,]\d+)?)\s*%")


def cmd_conferir(args) -> None:
    plano = json.loads(Path(args.plano).read_text(encoding="utf-8"))
    grade = json.loads(Path(args.grade).read_text(encoding="utf-8"))
    defeitos: list[str] = []

    itens = {i["num"]: i for i in plano["itens"]}
    aulas = grade.get("aulas", [])
    if not aulas:
        defeitos.append("grade.json não tem aulas")
    omitidos = {o["num"] if isinstance(o, dict) else o for o in grade.get("omitidos", [])}

    por_item = defaultdict(list)
    vistos = set()
    for a in aulas:
        aid = a.get("id")
        if not aid or aid in vistos:
            defeitos.append(f"aula com id ausente ou repetido: {aid!r}")
        vistos.add(aid)
        item = a.get("item") or a.get("num")
        if item not in itens:
            defeitos.append(f"aula {aid}: item '{item}' não existe no plano")
            continue
        por_item[item].append(a)
        if a.get("importancia") != itens[item]["importancia"]:
            defeitos.append(f"aula {aid}: importância {a.get('importancia')} ≠ "
                            f"{itens[item]['importancia']} do plano")

    for num, item in itens.items():
        if num not in por_item and num not in omitidos:
            defeitos.append(f"item {num} ({item['rotulo']}) não virou aula nem foi omitido "
                            "com justificativa")
            continue
        if num in por_item:
            somado = sum(int(a.get("minutos") or 0) for a in por_item[num])
            if abs(somado - item["minutos"]) > 2:
                defeitos.append(f"item {num}: as aulas somam {somado} min, o plano pede "
                                f"{item['minutos']} min")
            if len(por_item[num]) != item["aulas"]:
                defeitos.append(f"item {num}: {len(por_item[num])} aula(s), o plano pede "
                                f"{item['aulas']}")

    seq_de = {}
    for a in aulas:
        item = a.get("item") or a.get("num")
        if item in itens:
            seq_de.setdefault(item, []).append(int(a.get("seq") or 0))
    id_para_num = {i["id"]: i["num"] for i in plano["itens"]}
    for num, item in itens.items():
        if num not in seq_de:
            continue
        primeira = min(seq_de[num])
        for pre_id in item["requer"]:
            pre_num = id_para_num.get(pre_id)
            if pre_num in seq_de and max(seq_de[pre_num]) > primeira:
                defeitos.append(f"ordem violada: {num} começa em {primeira}, mas o "
                                f"pré-requisito {pre_num} só termina em {max(seq_de[pre_num])}")

    if args.sumario:
        texto = Path(args.sumario).read_text(encoding="utf-8")
        # a seção "Como ler a nota" explica a escada inteira: varrê-la tornaria o teste inútil
        texto = re.split(r"^#+\s*Como ler", texto, maxsplit=1, flags=re.M | re.I)[0]
        notas_validas = {i["importancia"] for i in plano["itens"]} | \
                        {round(m["importancia_media"]) for m in plano["modulos"]}
        for m in RE_NOTA.finditer(texto):
            if int(m.group(1)) not in notas_validas:
                defeitos.append(f"sumário: nota {m.group(0)} não existe no plano")
        pcts = {round(i["share"] * 100, 1) for i in plano["itens"]}
        for c in plano["cobertura"]["curva"]:      # o acumulado e o que ainda falta cobrir
            pcts |= {round(c["acumulado"] * 100, 1), round(c.get("restante", 0) * 100, 1)}
        pcts |= {round(float(c.strip('%')), 1) for c in plano["cobertura"]["marcos"]}
        pcts |= {0.0, 100.0}
        for m in RE_PCT.finditer(texto):
            valor = round(float(m.group(1).replace(",", ".")), 1)
            if not any(abs(valor - p) <= 0.15 for p in pcts):
                defeitos.append(f"sumário: o percentual {m.group(0)} não sai do plano")

    if defeitos:
        print(f"REPROVADO — {len(defeitos)} defeito(s):", file=sys.stderr)
        for d in defeitos:
            print(f"  ✗ {d}", file=sys.stderr)
        raise SystemExit(2)
    print(f"APROVADO — {len(itens)} item(ns), {len(aulas)} aula(s), ordem e números conferem.")


# --- CLI ------------------------------------------------------------------


def cmd_priorizar(args) -> None:
    try:
        g = carregar(args.alvo)
    except ErroDeLeitura as e:
        erro(str(e))
    par = {"minutos_aula": args.minutos_aula, "beta_centralidade": args.beta,
           "gama": args.gama, "coesao": args.coesao, "damping": args.damping,
           "cortes": sorted(float(c) for c in args.cortes.split(",")), "data": args.data}
    plano = priorizar(g, args.assunto, par, importar_prereq=not args.sem_prerequisitos)
    texto = json.dumps(plano, ensure_ascii=False, indent=2)
    if args.saida:
        destino = Path(args.saida)
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(texto + "\n", encoding="utf-8")
        t = plano["totais"]
        print(f"{args.saida}: {t['itens']} itens, {t['aulas']} aulas, {t['horas']} h, "
              f"importância média {t['importancia_media']}")
        marcos = plano["cobertura"]["marcos"]
        print("  cobertura: " + ", ".join(f"{k} em {v} itens" for k, v in marcos.items() if v))
        somados = sum(len(v) if isinstance(v, list) else 0 for v in plano["lacunas"].values())
        if somados:
            print(f"  lacunas: {somados} registro(s) — veja o bloco `lacunas` do plano")
    else:
        print(texto)


def main() -> None:
    ap = argparse.ArgumentParser(prog="sumario.py", description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("inspecionar", help="o que o grafo tem antes de priorizar")
    s.add_argument("alvo", help="grafo.md, diretório do grafo ou slug em grafos/")
    s.set_defaults(func=cmd_inspecionar)

    s = sub.add_parser("priorizar", help="calcula importância, fila e cobertura")
    s.add_argument("alvo")
    s.add_argument("--assunto", required=True, help="rótulo ou id do nó; 'tudo' para o grafo todo")
    s.add_argument("--minutos-aula", type=int, default=PADROES["minutos_aula"])
    s.add_argument("--beta", type=float, default=PADROES["beta_centralidade"],
                   help="peso da centralidade no valor (0 = só incidência)")
    s.add_argument("--gama", type=float, default=PADROES["gama"],
                   help="curvatura da escada 1–10")
    s.add_argument("--coesao", type=float, default=PADROES["coesao"])
    s.add_argument("--damping", type=float, default=PADROES["damping"])
    s.add_argument("--cortes", default="0.50,0.70,0.90")
    s.add_argument("--sem-prerequisitos", action="store_true",
                   help="não importa pré-requisitos de fora do assunto")
    s.add_argument("--data", help="AAAA-MM-DD gravado em gerado_em (padrão: hoje)")
    s.add_argument("--saida", help="grava o plano.json em vez de imprimir")
    s.set_defaults(func=cmd_priorizar)

    s = sub.add_parser("conferir", help="valida a grade e o sumário contra o plano")
    s.add_argument("--plano", required=True)
    s.add_argument("--grade", required=True)
    s.add_argument("--sumario")
    s.set_defaults(func=cmd_conferir)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
